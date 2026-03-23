"""
管理端路由 — 配置管理
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from app.config import config
from app.auth.dependencies import verify_admin

router = APIRouter(prefix="/admin/config", tags=["Admin Config"])
settings_router = APIRouter(prefix="/admin/settings", tags=["Admin Settings"])


class ConfigUpdateRequest(BaseModel):
    """可更新的配置项"""
    project: Optional[dict] = Field(None, description="项目配置，如 {\"name\": \"xxx\"}")
    agent: Optional[dict] = Field(None, description="Agent 配置，如 {\"registration_token\": \"xxx\", \"allow_registration\": true}")
    notification: Optional[dict] = Field(None, description="通知配置")
    webui: Optional[dict] = Field(None, description="WebUI 配置")
    workspace: Optional[dict] = Field(None, description="工作目录配置，如 {\"root\": \"/path\"}")
    server: Optional[dict] = Field(None, description="服务配置，如 {\"external_url\": \"https://...\"}")


class PasswordUpdateRequest(BaseModel):
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, description="新密码（至少6位）")


@router.get("", summary="获取系统配置")
async def get_config(_=Depends(verify_admin)):
    """
    获取当前系统配置（脱敏）。
    密码字段显示为 ***，注册令牌原样返回（管理员需要查看）。
    """
    return config.get_safe_config()


@router.put("", summary="更新系统配置")
async def update_config(req: ConfigUpdateRequest, _=Depends(verify_admin)):
    """
    批量更新系统配置。仅允许更新以下配置组：
    project, agent, notification, webui, workspace。

    不允许通过此接口更新密码（请使用 /password 接口）、
    server/database 配置（需手动修改 config.yaml 后重启）。

    更新后立即生效，无需重启。
    """
    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="未提供任何配置项")

    try:
        config.update(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "配置已更新", "updated_keys": list(data.keys())}


@router.put("/password", summary="修改管理员密码")
async def update_password(req: PasswordUpdateRequest, _=Depends(verify_admin)):
    """
    修改管理员密码。需要提供当前密码进行验证。
    修改后当前登录 token 仍然有效（无需重新登录）。
    """
    try:
        config.update_password(req.old_password, req.new_password)
    except ValueError:
        raise HTTPException(status_code=403, detail="当前密码错误")

    return {"message": "密码修改成功"}


# ── OpenClaw 设置 ──────────────────────────────────────────────────────────────

class OpenClawSettingsRequest(BaseModel):
    gateway_url: str = Field(..., description="OpenClaw 网关地址")
    gateway_token: str = Field(..., description="OpenClaw 网关 Token")


@settings_router.get("/openclaw", summary="获取 OpenClaw 网关配置")
async def get_openclaw_settings(_=Depends(verify_admin)):
    """
    获取当前 OpenClaw 网关地址和 Token。
    """
    return {
        "gateway_url": config.openclaw_gateway_url,
        "gateway_token": config.openclaw_gateway_token,
    }


@settings_router.post("/openclaw", summary="保存 OpenClaw 网关配置")
async def save_openclaw_settings(req: OpenClawSettingsRequest, _=Depends(verify_admin)):
    """
    保存 OpenClaw 网关地址和 Token。
    立即写入 config.yaml 并更新内存配置，无需重启。
    """
    with config._lock:
        if "openclaw" not in config._data:
            config._data["openclaw"] = {}
        config._data["openclaw"]["gateway_url"] = req.gateway_url
        config._data["openclaw"]["gateway_token"] = req.gateway_token
        config._save()

    return {"message": "OpenClaw 配置已保存"}
