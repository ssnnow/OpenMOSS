"""
一键创建 / 删除 OpenClaw Agent 路由

POST  /api/admin/agents/provision       — 创建 Agent（含 cron 唤醒）
DELETE /api/admin/agents/provision/{id} — 删除 Agent（清理 cron + OpenClaw + DB）
"""
from __future__ import annotations

import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.config import config
from app.database import get_db
from app.models.agent import Agent
from app.services.agent_service import generate_api_key
from app.services.openclaw_client import OpenClawClient, OpenClawError


router = APIRouter(prefix="/admin/agents", tags=["Admin Agent Provision"])


# ---------------------------------------------------------------------------
# 辅助：单例客户端（每次请求从 config 读取，支持热更新配置）
# ---------------------------------------------------------------------------

def _get_client() -> OpenClawClient:
    return OpenClawClient(
        gateway_url=config.openclaw_gateway_url,
        gateway_token=config.openclaw_gateway_token,
    )


# ---------------------------------------------------------------------------
# 间隔映射
# ---------------------------------------------------------------------------

INTERVAL_MS: dict[str, int] = {
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "24h": 86_400_000,
}


def _interval_to_ms(interval: str) -> int:
    ms = INTERVAL_MS.get(interval)
    if ms is None:
        raise ValueError(
            f"无效的 wake_interval '{interval}'，支持: {', '.join(INTERVAL_MS)}"
        )
    return ms


# ---------------------------------------------------------------------------
# SOUL.md 模板
# ---------------------------------------------------------------------------

_SOUL_TEMPLATE = """\
# SOUL.md — {name}

## 角色定位

你是 **{name}**，一名专注于以下职责的 AI Agent：

> {role}

## 工作方式

- 接收任务后，先理解目标，再制定计划，逐步执行
- 遇到不确定的情况，优先查询相关资料，再做决策
- 输出结果时，保持简洁清晰，突出重点
- 始终以完成任务、产出价值为核心目标

## 个性特征

- **专注**：深度聚焦当前任务，不跑题
- **务实**：以结果为导向，避免过度设计
- **自省**：每次执行后回顾，持续优化

---

*由 OpenMOSS 一键创建*
"""


def _generate_soul(name: str, role: str) -> str:
    return _SOUL_TEMPLATE.format(name=name, role=role)


# ---------------------------------------------------------------------------
# 请求 / 响应 Schema
# ---------------------------------------------------------------------------

class ProvisionRequest(BaseModel):
    name: str = Field(..., description="Agent 名称", max_length=100)
    role: str = Field(..., description="Agent 职责描述（用于生成 SOUL.md）")
    wake_interval: str = Field("1h", description="唤醒间隔: 15m/30m/1h/4h/24h")


class ProvisionResponse(BaseModel):
    id: str
    name: str
    role: str
    description: str
    api_key: str
    openclaw_agent_id: Optional[str]
    openclaw_cron_job_id: Optional[str]
    wake_interval: Optional[str]


# ---------------------------------------------------------------------------
# POST /api/admin/agents/provision
# ---------------------------------------------------------------------------

@router.post(
    "/provision",
    response_model=ProvisionResponse,
    status_code=201,
    summary="一键创建 OpenClaw Agent（含 cron 唤醒）",
)
async def provision_agent(
    req: ProvisionRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """
    1. 在 OpenClaw 创建 Agent
    2. 为 Agent 注册周期性唤醒 cron job
    3. 在 OpenMOSS DB 注册 Agent 记录
    出错时尽力回滚 OpenClaw 侧资源。
    """
    client = _get_client()

    # ① 检查 OpenClaw 是否已配置
    if not client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="OpenClaw gateway_token 未配置，请在 config.yaml 中设置 openclaw.gateway_token",
        )

    # ② 校验 wake_interval
    try:
        every_ms = _interval_to_ms(req.wake_interval)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # ③ 检查 OpenMOSS 是否已有同名 Agent
    existing = db.query(Agent).filter(Agent.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"名称 '{req.name}' 已被注册")

    # ④ 生成 SOUL.md
    soul_content = _generate_soul(req.name, req.role)

    # ⑤ 创建 OpenClaw Agent
    openclaw_agent_id: Optional[str] = None
    openclaw_cron_job_id: Optional[str] = None

    try:
        agent_result = await client.create_agent(
            name=req.name,
            description=req.role,
            soul=soul_content,
        )
        openclaw_agent_id = agent_result["agentId"]
    except OpenClawError as exc:
        raise HTTPException(status_code=502, detail=f"OpenClaw 创建 Agent 失败: {exc}")

    # ⑥ 创建 cron 唤醒
    wake_message = (
        f"你好 {req.name}，这是你的定期唤醒信号。请检查当前任务状态，"
        "完成待处理工作，并记录进展。"
    )
    try:
        cron_result = await client.create_cron(
            agent_id=openclaw_agent_id,
            name=f"Wake {req.name}",
            every_ms=every_ms,
            wake_message=wake_message,
        )
        openclaw_cron_job_id = cron_result["jobId"]
    except OpenClawError as exc:
        # 回滚：删除刚创建的 OpenClaw Agent
        try:
            await client.delete_agent(openclaw_agent_id)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"OpenClaw 创建 cron 失败: {exc}")

    # ⑦ 在 OpenMOSS DB 注册 Agent
    # role 字段存为固定值 "executor"（OpenMOSS 角色体系），role 描述存 description
    db_agent = Agent(
        id=str(uuid.uuid4()),
        name=req.name,
        role="executor",
        description=req.role,
        api_key=generate_api_key(),
        openclaw_agent_id=openclaw_agent_id,
        openclaw_cron_job_id=openclaw_cron_job_id,
        wake_interval=req.wake_interval,
    )
    try:
        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)
    except Exception as exc:
        db.rollback()
        # 回滚 OpenClaw 侧资源
        try:
            await client.delete_cron(openclaw_cron_job_id)
        except Exception:
            pass
        try:
            await client.delete_agent(openclaw_agent_id)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"DB 写入失败: {exc}")

    return ProvisionResponse(
        id=db_agent.id,
        name=db_agent.name,
        role=db_agent.role,
        description=db_agent.description,
        api_key=db_agent.api_key,
        openclaw_agent_id=db_agent.openclaw_agent_id,
        openclaw_cron_job_id=db_agent.openclaw_cron_job_id,
        wake_interval=db_agent.wake_interval,
    )


# ---------------------------------------------------------------------------
# DELETE /api/admin/agents/provision/{agent_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/provision/{agent_id}",
    summary="一键删除 OpenClaw Agent（含 cron + DB）",
)
async def deprovision_agent(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """
    1. cron.remove（best effort）
    2. agents.remove（best effort）
    3. 从 OpenMOSS DB 删除 Agent 记录
    """
    db_agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not db_agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")

    client = _get_client()

    # ① 删除 cron（best effort）
    if db_agent.openclaw_cron_job_id and client.is_configured():
        try:
            await client.delete_cron(db_agent.openclaw_cron_job_id)
        except OpenClawError:
            pass  # 已删除或不存在，忽略

    # ② 删除 OpenClaw Agent（best effort）
    if db_agent.openclaw_agent_id and client.is_configured():
        try:
            await client.delete_agent(db_agent.openclaw_agent_id)
        except OpenClawError:
            pass

    # ③ 从 DB 删除（不级联清理关联数据，保留历史记录）
    db.delete(db_agent)
    db.commit()

    return {"ok": True}
