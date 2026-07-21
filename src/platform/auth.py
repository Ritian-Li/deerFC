# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.db import get_session
from src.platform.models import ActivationCode, ModelEntry, Plan, User, utcnow

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"
JWT_TTL_DAYS = 30

_jwt_secret = os.getenv("PLATFORM_JWT_SECRET", "")
if not _jwt_secret:
    _jwt_secret = secrets.token_hex(32)
    logger.warning(
        "PLATFORM_JWT_SECRET is not set; using an ephemeral secret. "
        "All logins will be invalidated on restart."
    )


# --- brute-force protection: sliding window per IP, in-process ---
_ATTEMPT_WINDOW_SECONDS = 300
_ATTEMPT_LIMIT = 10
_attempts: dict[str, deque] = defaultdict(deque)


def check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _attempts[ip]
    while window and now - window[0] > _ATTEMPT_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= _ATTEMPT_LIMIT:
        raise HTTPException(status_code=429, detail="尝试过于频繁，请 5 分钟后再试")
    window.append(now)


def normalize_code(code: str) -> str:
    return code.strip().upper().replace(" ", "").replace("-", "")


def format_code(code: str) -> str:
    raw = normalize_code(code)
    return "-".join(raw[i : i + 6] for i in range(0, len(raw), 6))


def issue_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "jti": user.session_id,
        "exp": utcnow() + timedelta(days=JWT_TTL_DAYS),
    }
    return jwt.encode(payload, _jwt_secret, algorithm=JWT_ALGORITHM)


async def get_current_user(
    request: Request, session: AsyncSession = Depends(get_session)
) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = jwt.decode(auth[7:], _jwt_secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="登录已失效，请重新输入卡密")
    user = await session.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="账号不存在")
    if payload.get("jti") != user.session_id:
        raise HTTPException(status_code=401, detail="账号已在其他设备登录")
    if user.banned:
        raise HTTPException(status_code=403, detail="账号已被停用，请联系卖家")
    return user


class SessionRequest(BaseModel):
    code: str = Field(..., min_length=8, max_length=40)


async def build_profile(session: AsyncSession, user: User) -> dict:
    model = await session.get(ModelEntry, user.model_id)
    return {
        "user_id": user.id,
        "remaining_uses": user.remaining_uses,
        "expires_at": user.expires_at.isoformat() + "Z",
        "expired": user.expires_at < utcnow(),
        "model": model.display_name if model else "",
        "provider": model.provider if model else "",
    }


async def _load_code(session: AsyncSession, raw_code: str) -> ActivationCode | None:
    result = await session.execute(
        select(ActivationCode).where(ActivationCode.code == format_code(raw_code))
    )
    return result.scalar_one_or_none()


async def activate_or_login(session: AsyncSession, raw_code: str) -> tuple[User, bool]:
    """卡密即账号：未激活的卡密走激活建号，已激活的走登录。返回 (user, is_new)."""
    card = await _load_code(session, raw_code)
    if card is None or card.status == ActivationCode.STATUS_VOID:
        raise HTTPException(status_code=401, detail="卡密无效，请核对后重试")

    if card.status == ActivationCode.STATUS_ACTIVATED:
        user = await session.get(User, card.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="卡密数据异常，请联系卖家")
        if user.banned:
            raise HTTPException(status_code=403, detail="账号已被停用，请联系卖家")
        # 新登录踢掉旧会话（单活跃 session，防合买共享）
        user.session_id = str(uuid.uuid4())
        await session.commit()
        return user, False

    plan = await session.get(Plan, card.plan_id)
    if plan is None:
        raise HTTPException(status_code=500, detail="套餐配置缺失，请联系卖家")
    user = User(
        model_id=card.model_id,
        remaining_uses=plan.total_uses,
        expires_at=utcnow() + timedelta(minutes=plan.valid_minutes),
        token_reserve=plan.token_reserve,
        session_id=str(uuid.uuid4()),
    )
    session.add(user)
    await session.flush()
    card.status = ActivationCode.STATUS_ACTIVATED
    card.user_id = user.id
    card.activated_at = utcnow()
    await session.commit()
    return user, True


async def renew(session: AsyncSession, user: User, raw_code: str) -> User:
    """续费：次数叠加、有效期取 max、隐藏 token 余量叠加；新卡的模型覆盖生效."""
    card = await _load_code(session, raw_code)
    if card is None or card.status != ActivationCode.STATUS_UNUSED:
        raise HTTPException(status_code=400, detail="该卡密无效或已被使用")
    plan = await session.get(Plan, card.plan_id)
    if plan is None:
        raise HTTPException(status_code=500, detail="套餐配置缺失，请联系卖家")

    user.remaining_uses += plan.total_uses
    user.expires_at = max(user.expires_at, utcnow()) + timedelta(
        minutes=plan.valid_minutes
    )
    if plan.token_reserve:
        user.token_reserve = max(user.token_reserve, 0) + plan.token_reserve
    user.model_id = card.model_id
    card.status = ActivationCode.STATUS_ACTIVATED
    card.user_id = user.id
    card.activated_at = utcnow()
    await session.commit()
    return user
