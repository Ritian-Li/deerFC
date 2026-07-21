# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    # naive UTC everywhere: SQLite drops tzinfo, mixing aware/naive breaks comparisons
    return datetime.now(timezone.utc).replace(tzinfo=None)


_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_card_code() -> str:
    # 24 chars of base36 ≈ 124 bits of entropy; grouped for readability
    raw = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(24))
    return "-".join(raw[i : i + 6] for i in range(0, 24, 6))


class Base(DeclarativeBase):
    pass


class Plan(Base):
    """套餐模板：对外只有次数 + 有效天数，token 上限是内部风控参数."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    total_uses: Mapped[int] = mapped_column(Integer)
    valid_days: Mapped[int] = mapped_column(Integer)
    # 隐藏的套餐总 token 熔断（0 = 不限，仅靠单任务 cap 与每日全局熔断兜底）
    token_reserve: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ModelEntry(Base):
    """模型注册表：display_name 必须与真实上游 model_name 一致（宣传=实际调用）."""

    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(64))
    model_name: Mapped[str] = mapped_column(String(128))
    base_url: Mapped[str] = mapped_column(String(256))
    # 环境变量名而非明文 key，如 "VOLCENGINE_ARK_API_KEY"
    api_key_env: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(32), default="")  # 火山方舟/阿里云百炼
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ActivationCode(Base):
    __tablename__ = "activation_codes"

    STATUS_UNUSED = "unused"
    STATUS_ACTIVATED = "activated"
    STATUS_VOID = "void"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"))
    # 闲鱼订单号/旺旺名备注，丢卡找回的唯一线索
    order_ref: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default=STATUS_UNUSED)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class User(Base):
    """卡密即账号：首张卡激活时创建，配额直接挂在用户上."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"))
    remaining_uses: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    # 隐藏 token 余量（0 = 不限）；买家不可见，仅内部熔断用
    token_reserve: Mapped[int] = mapped_column(Integer, default=0)
    banned: Mapped[bool] = mapped_column(Boolean, default=False)
    # 单活跃会话：JWT jti 与此不符即被踢下线
    session_id: Mapped[str] = mapped_column(String(36), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Thread(Base):
    __tablename__ = "threads"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Run(Base):
    """一次完整 workflow 执行 = 一条流水，兼作 usage ledger 与产物存储."""

    __tablename__ = "runs"

    STATUS_RUNNING = "running"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_REJECTED = "rejected"  # 并发/审核拒绝，未执行

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    thread_id: Mapped[str] = mapped_column(String(64), index=True)
    skill: Mapped[str] = mapped_column(String(32), default="research")
    model_name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default=STATUS_RUNNING)
    # 成功才扣次数；charged 标记本 run 是否已计次
    charged: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    result_md: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
