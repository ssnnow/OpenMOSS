"""
Onboarding 路由 — 帮助新 Agent 快速接入 OpenMOSS

提供两个端点：
  POST /admin/agents/create-openclaw   — 注册 Agent 并返回 OpenClaw 接入指南
  GET  /admin/agents/onboard-guide     — 通用接入文档（不依赖具体 Agent）
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.auth.dependencies import verify_admin
from app.services import agent_service
from app.config import config

router = APIRouter(prefix="/admin/agents", tags=["Onboarding"])


# ============================================================
# 请求 / 响应模型
# ============================================================

class CreateOpenClawAgentRequest(BaseModel):
    role: str = Field(..., description="代理角色: planner | executor | reviewer | patrol")
    name: str = Field(..., description="代理名称", max_length=100)
    cron_schedule: Optional[str] = Field(None, description="Cron 表达式，如 '*/30 * * * *'")


class CreateOpenClawAgentResponse(BaseModel):
    role: str
    name: str
    skill_zip_name: str
    registration_token: str
    api_url_hint: str
    openclaw_setup_steps: List[str]


class OnboardingGuideStep(BaseModel):
    step: int
    title: str
    instruction: str


class OnboardingGuideResponse(BaseModel):
    title: str
    description: str
    roles: dict
    steps: List[OnboardingGuideStep]


# ============================================================
# 辅助函数
# ============================================================

VALID_ROLES = ["planner", "executor", "reviewer", "patrol"]

ROLE_DESCRIPTIONS = {
    "planner":  "规划者 — 拆解需求、创建模块与子任务、分配给执行者、收尾交付",
    "executor": "执行者 — 认领子任务、执行开发工作、提交交付物等待审查",
    "reviewer": "审查者 — 检查交付物质量、评分、通过或驳回返工",
    "patrol":   "巡查者 — 定时巡检系统异常、标记阻塞任务、发送告警通知",
}

DEFAULT_CRON = {
    "planner":  "*/15 * * * *",
    "executor": "*/10 * * * *",
    "reviewer": "*/10 * * * *",
    "patrol":   "*/30 * * * *",
}


def _skill_zip_name(role: str) -> str:
    """返回该角色对应的 Skill 压缩包文件名"""
    return f"task-{role}-skill.zip"


def _api_url_hint() -> str:
    """返回 OpenMOSS API 基础地址提示（优先使用外网地址）"""
    return config.server_external_url


def _build_setup_steps(
    role: str,
    name: str,
    api_key: str,
    registration_token: str,
    cron_schedule: Optional[str],
) -> List[str]:
    """
    生成面向零技术背景用户的、可直接复制粘贴的接入步骤。
    每条字符串都是完整的操作说明，不需要额外解释。
    """
    api_url = _api_url_hint()
    zip_name = _skill_zip_name(role)
    cron = cron_schedule or DEFAULT_CRON.get(role, "*/15 * * * *")

    steps = [
        # 步骤 1：安装 OpenClaw
        (
            "【第 1 步】安装 OpenClaw CLI\n"
            "在终端（命令行）中运行以下命令安装 OpenClaw：\n\n"
            "    npm install -g openclaw\n\n"
            "如果已经安装过，请跳过此步骤。"
        ),

        # 步骤 2：下载 Skill 包
        (
            f"【第 2 步】下载 {role} 角色的 Skill 包\n"
            f"运行以下命令，将 Skill 压缩包下载到当前目录：\n\n"
            f"    curl -L -o {zip_name} \"{api_url}/api/skills/{zip_name}\"\n\n"
            f"下载完成后，当前目录会出现文件：{zip_name}"
        ),

        # 步骤 3：安装 Skill
        (
            f"【第 3 步】将 Skill 包安装到 OpenClaw\n"
            f"运行以下命令将下载好的 Skill 包安装到 OpenClaw：\n\n"
            f"    openclaw skill install {zip_name}\n\n"
            f"安装成功后会提示 Skill 已加载。"
        ),

        # 步骤 4：注册 Agent（告知 registration_token）
        (
            f"【第 4 步】向 OpenMOSS 注册你的 Agent\n"
            f"OpenClaw 启动时会自动调用 OpenMOSS 的注册接口。你需要把以下信息告诉 OpenClaw：\n\n"
            f"  • OpenMOSS 地址：{api_url}\n"
            f"  • 注册令牌（registration_token）：{registration_token}\n\n"
            f"在 OpenClaw 的设置或对话中，将上述两项填入对应字段即可。"
        ),

        # 步骤 5：配置 API Key（已预先分配好）
        (
            f"【第 5 步】配置 Agent API Key\n"
            f"你的 Agent「{name}」已经在 OpenMOSS 中创建完毕，API Key 如下：\n\n"
            f"    {api_key}\n\n"
            f"请将此 API Key 保存好，并在 OpenClaw 的 Skill 设置中填入（通常在 SKILL.md 的"
            f"「认证信息」一节）。注意：此 Key 只会显示一次，请立即复制保存。"
        ),

        # 步骤 6：配置 Cron 定时唤醒
        (
            f"【第 6 步】设置定时自动唤醒（Cron）\n"
            f"OpenMOSS 的 Agent 通过定时唤醒自主工作，建议使用以下 Cron 表达式：\n\n"
            f"    {cron}\n\n"
            f"在 OpenClaw 的 Cron 设置页面，将上方表达式填入「{name}」对应的 Cron 字段，"
            f"保存后 Agent 会按计划自动运行。"
        ),

        # 步骤 7：验证
        (
            f"【第 7 步】验证 Agent 是否正常工作\n"
            f"完成以上步骤后，你可以：\n\n"
            f"  1. 打开 OpenMOSS 管理后台：{api_url}\n"
            f"  2. 进入「Agent」页面，找到「{name}」\n"
            f"  3. 确认状态为「active」\n"
            f"  4. 等待第一次 Cron 触发后，在「活动流」页面查看 Agent 的实际运行记录\n\n"
            f"如果 Agent 的状态是 active 并且有活动记录，说明接入成功！"
        ),
    ]

    return steps


# ============================================================
# API 端点
# ============================================================

@router.post(
    "/create-openclaw",
    response_model=CreateOpenClawAgentResponse,
    summary="创建 OpenClaw Agent 并获取接入指南",
)
async def create_openclaw_agent(
    req: CreateOpenClawAgentRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """
    在 OpenMOSS 中注册一个新的 Agent，并返回面向零技术背景用户的、
    可直接复制粘贴的 OpenClaw 接入指南（openclaw_setup_steps）。

    - **role**: planner / executor / reviewer / patrol
    - **name**: Agent 的显示名称
    - **cron_schedule**: 可选，Cron 表达式（留空则使用角色默认值）
    """
    if req.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"role 必须是以下之一: {', '.join(VALID_ROLES)}",
        )

    # 注册 Agent，获取 api_key
    try:
        agent = agent_service.register_agent(
            db,
            req.name,
            req.role,
            f"OpenClaw {req.role} agent — 通过 Onboarding API 创建",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent 创建失败: {exc}")

    registration_token = config.registration_token
    api_url_hint = _api_url_hint()
    zip_name = _skill_zip_name(req.role)

    setup_steps = _build_setup_steps(
        role=req.role,
        name=agent.name,
        api_key=agent.api_key,
        registration_token=registration_token,
        cron_schedule=req.cron_schedule,
    )

    return CreateOpenClawAgentResponse(
        role=agent.role,
        name=agent.name,
        skill_zip_name=zip_name,
        registration_token=registration_token,
        api_url_hint=api_url_hint,
        openclaw_setup_steps=setup_steps,
    )


@router.get(
    "/onboard-guide",
    response_model=OnboardingGuideResponse,
    summary="获取通用 Agent 接入指南",
)
async def get_onboarding_guide():
    """
    返回一份通用的 Agent 接入手册，描述各角色职责与完整的接入流程。
    此端点无需鉴权，方便在正式注册前查阅。
    """
    api_url = _api_url_hint()

    steps = [
        OnboardingGuideStep(
            step=1,
            title="安装 OpenClaw CLI",
            instruction=(
                "在你的机器上安装 OpenClaw 命令行工具。\n"
                "运行命令：npm install -g openclaw\n"
                "（需要 Node.js 18 或更高版本）"
            ),
        ),
        OnboardingGuideStep(
            step=2,
            title="通过管理后台创建 Agent",
            instruction=(
                f"打开 OpenMOSS 管理后台：{api_url}\n"
                "登录后，进入「Onboarding」或「Agent 管理」页面，\n"
                "选择角色（planner / executor / reviewer / patrol），\n"
                "填写 Agent 名称，点击「创建」。\n"
                "系统会为你生成 API Key 和完整的接入步骤，直接复制粘贴即可。"
            ),
        ),
        OnboardingGuideStep(
            step=3,
            title="下载并安装对应角色的 Skill 包",
            instruction=(
                "系统会告诉你对应的 Skill 压缩包名称，例如 task-executor-skill.zip。\n"
                f"下载地址：{api_url}/api/skills/task-{{role}}-skill.zip\n"
                "下载后运行：openclaw skill install task-{role}-skill.zip"
            ),
        ),
        OnboardingGuideStep(
            step=4,
            title="在 OpenClaw 中填入 OpenMOSS 地址和注册令牌",
            instruction=(
                f"OpenMOSS 服务地址：{api_url}\n"
                "注册令牌（registration_token）：创建 Agent 时系统会显示，直接复制。\n"
                "将上述两项填入 OpenClaw 的设置页面。"
            ),
        ),
        OnboardingGuideStep(
            step=5,
            title="配置 Agent API Key",
            instruction=(
                "创建 Agent 时系统会生成唯一的 API Key。\n"
                "将 API Key 填入 OpenClaw Skill 目录下的 SKILL.md「认证信息」部分。\n"
                "格式示例：API_KEY: sk-xxxxxxxx"
            ),
        ),
        OnboardingGuideStep(
            step=6,
            title="设置 Cron 定时唤醒",
            instruction=(
                "在 OpenClaw 的 Cron 设置中，为 Agent 添加定时任务。\n"
                "推荐 Cron 表达式：\n"
                "  • planner:  */15 * * * *（每 15 分钟）\n"
                "  • executor: */10 * * * *（每 10 分钟）\n"
                "  • reviewer: */10 * * * *（每 10 分钟）\n"
                "  • patrol:   */30 * * * *（每 30 分钟）"
            ),
        ),
        OnboardingGuideStep(
            step=7,
            title="验证接入成功",
            instruction=(
                f"打开 OpenMOSS 管理后台：{api_url}\n"
                "进入「Agent」页面，找到你创建的 Agent，确认状态为「active」。\n"
                "Cron 触发后，在「活动流」页面可以看到 Agent 的运行记录。\n"
                "出现活动记录 = 接入成功！"
            ),
        ),
    ]

    return OnboardingGuideResponse(
        title="OpenMOSS Agent 接入指南",
        description=(
            "本指南帮助你从零开始接入一个 OpenClaw Agent 到 OpenMOSS 任务调度平台。"
            "每一步都提供了可直接复制粘贴的命令和说明，无需任何技术背景。"
        ),
        roles=ROLE_DESCRIPTIONS,
        steps=steps,
    )
