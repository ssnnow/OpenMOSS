"""
OpenClaw 网关 HTTP 客户端

负责通过 OpenClaw Gateway 的 /tools/invoke 接口调用远程工具：
- agents.add / agents.remove
- cron.add / cron.remove
"""
from __future__ import annotations

import httpx


class OpenClawError(Exception):
    """OpenClaw API 调用失败"""


class OpenClawClient:
    """轻量级异步 OpenClaw Gateway 客户端"""

    def __init__(self, gateway_url: str, gateway_token: str):
        self._base_url = gateway_url.rstrip("/")
        self._token = gateway_token

    def is_configured(self) -> bool:
        """返回 False 表示 gateway_token 未配置，功能不可用"""
        return bool(self._token)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _invoke(self, tool: str, args: dict) -> dict:
        """调用 POST /tools/invoke，返回 result 字段内容"""
        url = f"{self._base_url}/tools/invoke"
        payload = {"tool": tool, "args": args}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=self._headers())
            except httpx.RequestError as exc:
                raise OpenClawError(f"网络请求失败: {exc}") from exc

        if resp.status_code >= 400:
            raise OpenClawError(
                f"OpenClaw API 返回错误 {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        # 兼容两种返回结构：{ result: {...} } 或直接 {...}
        return data.get("result", data)

    # ------------------------------------------------------------------
    # agents.add
    # ------------------------------------------------------------------

    async def create_agent(self, name: str, description: str, soul: str) -> dict:
        """创建 OpenClaw Agent，返回 { agentId: str }"""
        result = await self._invoke(
            "agents.add",
            {
                "name": name,
                "description": description,
                "soul": soul,
            },
        )
        if "agentId" not in result:
            raise OpenClawError(f"agents.add 返回数据缺少 agentId: {result}")
        return result

    # ------------------------------------------------------------------
    # cron.add
    # ------------------------------------------------------------------

    async def create_cron(
        self,
        agent_id: str,
        name: str,
        every_ms: int,
        wake_message: str,
    ) -> dict:
        """为指定 Agent 创建周期性唤醒 cron job，返回 { jobId: str }"""
        result = await self._invoke(
            "cron.add",
            {
                "name": name,
                "schedule": {"every": every_ms},
                "sessionTarget": "isolated",
                "agentId": agent_id,
                "payload": {
                    "kind": "agentTurn",
                    "message": wake_message,
                },
                "delivery": {"mode": "none"},
            },
        )
        if "jobId" not in result:
            raise OpenClawError(f"cron.add 返回数据缺少 jobId: {result}")
        return result

    # ------------------------------------------------------------------
    # cron.remove
    # ------------------------------------------------------------------

    async def delete_cron(self, job_id: str) -> None:
        """删除 cron job（best effort，忽略 404）"""
        try:
            await self._invoke("cron.remove", {"jobId": job_id})
        except OpenClawError as exc:
            # 已不存在时忽略
            if "404" not in str(exc):
                raise

    # ------------------------------------------------------------------
    # agents.remove
    # ------------------------------------------------------------------

    async def delete_agent(self, agent_id: str) -> None:
        """删除 OpenClaw Agent（best effort，忽略 404）"""
        try:
            await self._invoke("agents.remove", {"agentId": agent_id})
        except OpenClawError as exc:
            if "404" not in str(exc):
                raise
