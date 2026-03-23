"""
Agent 注册表模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, Index

from app.database import Base


class Agent(Base):
    __tablename__ = "agent"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, comment="Agent 名称")
    role = Column(String(20), nullable=False, index=True, comment="角色类型: planner/executor/reviewer/patrol")
    description = Column(Text, default="", comment="职责简要")
    status = Column(String(20), default="active", index=True, comment="状态: active/disabled")
    api_key = Column(String(64), unique=True, nullable=False, comment="API Key")
    total_score = Column(Integer, default=0, comment="累计积分")
    created_at = Column(DateTime, default=datetime.now, comment="注册时间")

    # OpenClaw 一键创建字段
    openclaw_agent_id = Column(String(128), nullable=True, comment="OpenClaw Agent ID")
    openclaw_cron_job_id = Column(String(128), nullable=True, comment="OpenClaw Cron Job ID")
    wake_interval = Column(String(20), nullable=True, comment="唤醒间隔，如 1h/4h/24h")
