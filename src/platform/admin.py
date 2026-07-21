# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.llms.llm import clear_model_cache_entry
from src.platform.db import get_session
from src.platform.models import (
    ActivationCode,
    ModelEntry,
    Plan,
    Run,
    User,
    generate_card_code,
    utcnow,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(x_admin_token: str = Header(default="")) -> None:
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    if x_admin_token != expected:
        raise HTTPException(status_code=403, detail="forbidden")


# ---------- models ----------


class ModelIn(BaseModel):
    display_name: str
    model_name: str
    base_url: str
    api_key_env: str
    provider: str = ""
    active: bool = True


@router.post("/models", dependencies=[Depends(require_admin)])
async def create_model(body: ModelIn, session: AsyncSession = Depends(get_session)):
    entry = ModelEntry(**body.model_dump())
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return {"id": entry.id}


@router.get("/models", dependencies=[Depends(require_admin)])
async def list_models(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ModelEntry))
    return {
        "models": [
            {
                "id": m.id,
                "display_name": m.display_name,
                "model_name": m.model_name,
                "base_url": m.base_url,
                "api_key_env": m.api_key_env,
                "provider": m.provider,
                "active": m.active,
            }
            for m in result.scalars()
        ]
    }


class ModelPatch(BaseModel):
    display_name: Optional[str] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    provider: Optional[str] = None
    active: Optional[bool] = None


@router.patch("/models/{model_id}", dependencies=[Depends(require_admin)])
async def patch_model(
    model_id: int, body: ModelPatch, session: AsyncSession = Depends(get_session)
):
    entry = await session.get(ModelEntry, model_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="model not found")
    clear_model_cache_entry(entry.model_name, entry.base_url)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(entry, k, v)
    await session.commit()
    return {"ok": True}


# ---------- plans ----------


class PlanIn(BaseModel):
    name: str
    total_uses: int = Field(gt=0)
    valid_days: int = Field(gt=0)
    token_reserve: int = 0


@router.post("/plans", dependencies=[Depends(require_admin)])
async def create_plan(body: PlanIn, session: AsyncSession = Depends(get_session)):
    plan = Plan(**body.model_dump())
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return {"id": plan.id}


@router.get("/plans", dependencies=[Depends(require_admin)])
async def list_plans(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Plan))
    return {
        "plans": [
            {
                "id": p.id,
                "name": p.name,
                "total_uses": p.total_uses,
                "valid_days": p.valid_days,
                "token_reserve": p.token_reserve,
                "active": p.active,
            }
            for p in result.scalars()
        ]
    }


# ---------- activation codes (发货工作流) ----------


class CodesIn(BaseModel):
    plan_id: int
    model_id: int
    count: int = Field(default=1, gt=0, le=200)
    order_ref: str = ""


@router.post("/codes", dependencies=[Depends(require_admin)])
async def create_codes(body: CodesIn, session: AsyncSession = Depends(get_session)):
    if await session.get(Plan, body.plan_id) is None:
        raise HTTPException(status_code=404, detail="plan not found")
    if await session.get(ModelEntry, body.model_id) is None:
        raise HTTPException(status_code=404, detail="model not found")
    codes = []
    for _ in range(body.count):
        code = generate_card_code()
        session.add(
            ActivationCode(
                code=code,
                plan_id=body.plan_id,
                model_id=body.model_id,
                order_ref=body.order_ref,
            )
        )
        codes.append(code)
    await session.commit()
    return {"codes": codes}


@router.get("/codes", dependencies=[Depends(require_admin)])
async def find_codes(
    order_ref: str = "",
    status: str = "",
    session: AsyncSession = Depends(get_session),
):
    query = select(ActivationCode).order_by(ActivationCode.created_at.desc()).limit(100)
    if order_ref:
        query = query.where(ActivationCode.order_ref.contains(order_ref))
    if status:
        query = query.where(ActivationCode.status == status)
    result = await session.execute(query)
    return {
        "codes": [
            {
                "id": c.id,
                "code": c.code,
                "plan_id": c.plan_id,
                "model_id": c.model_id,
                "order_ref": c.order_ref,
                "status": c.status,
                "user_id": c.user_id,
                "created_at": c.created_at.isoformat() + "Z",
            }
            for c in result.scalars()
        ]
    }


@router.post("/codes/{code_id}/void", dependencies=[Depends(require_admin)])
async def void_code(code_id: int, session: AsyncSession = Depends(get_session)):
    code = await session.get(ActivationCode, code_id)
    if code is None:
        raise HTTPException(status_code=404, detail="code not found")
    if code.status == ActivationCode.STATUS_ACTIVATED:
        raise HTTPException(status_code=400, detail="code already activated")
    code.status = ActivationCode.STATUS_VOID
    await session.commit()
    return {"ok": True}


# ---------- users (售后) ----------


@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(User).order_by(User.created_at.desc()).limit(200)
    )
    return {
        "users": [
            {
                "id": u.id,
                "model_id": u.model_id,
                "remaining_uses": u.remaining_uses,
                "expires_at": u.expires_at.isoformat() + "Z",
                "token_reserve": u.token_reserve,
                "banned": u.banned,
                "created_at": u.created_at.isoformat() + "Z",
            }
            for u in result.scalars()
        ]
    }


class UserPatch(BaseModel):
    banned: Optional[bool] = None
    add_uses: Optional[int] = None
    extend_days: Optional[int] = None
    model_id: Optional[int] = None


@router.patch("/users/{user_id}", dependencies=[Depends(require_admin)])
async def patch_user(
    user_id: int, body: UserPatch, session: AsyncSession = Depends(get_session)
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if body.banned is not None:
        user.banned = body.banned
    if body.add_uses:
        user.remaining_uses += body.add_uses
    if body.extend_days:
        user.expires_at = max(user.expires_at, utcnow()) + timedelta(
            days=body.extend_days
        )
    if body.model_id is not None:
        if await session.get(ModelEntry, body.model_id) is None:
            raise HTTPException(status_code=404, detail="model not found")
        user.model_id = body.model_id
    await session.commit()
    return {"ok": True}


# ---------- stats (成本核算) ----------


@router.get("/stats/daily", dependencies=[Depends(require_admin)])
async def daily_stats(days: int = 14, session: AsyncSession = Depends(get_session)):
    since = utcnow() - timedelta(days=days)
    day = func.date(Run.created_at)
    result = await session.execute(
        select(
            day.label("day"),
            func.count(Run.id),
            func.sum(Run.total_tokens),
            func.sum(case((Run.charged, 1), else_=0)),
        )
        .where(Run.created_at >= since)
        .group_by(day)
        .order_by(day)
    )
    return {
        "days": [
            {
                "day": str(row[0]),
                "runs": row[1],
                "total_tokens": int(row[2] or 0),
                "charged_runs": int(row[3] or 0),
            }
            for row in result
        ]
    }
