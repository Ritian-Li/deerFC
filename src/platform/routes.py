# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.auth import (
    SessionRequest,
    activate_or_login,
    build_profile,
    check_rate_limit,
    get_current_user,
    issue_token,
    renew,
)
from src.platform.db import get_session
from src.platform.models import Run, User

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
runs_router = APIRouter(prefix="/api/runs", tags=["runs"])


@auth_router.post("/session")
async def create_session(
    body: SessionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """卡密即账号：未激活自动激活，已激活即登录（新登录踢旧会话）."""
    check_rate_limit(request)
    user, is_new = await activate_or_login(session, body.code)
    return {
        "token": issue_token(user),
        "is_new": is_new,
        "profile": await build_profile(session, user),
    }


@auth_router.post("/renew")
async def renew_quota(
    body: SessionRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    check_rate_limit(request)
    user = await session.merge(user)
    user = await renew(session, user, body.code)
    return {"profile": await build_profile(session, user)}


@auth_router.get("/me")
async def me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return {"profile": await build_profile(session, user)}


@runs_router.get("")
async def list_runs(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Run)
        .where(Run.user_id == user.id)
        .order_by(Run.created_at.desc())
        .limit(50)
    )
    return {
        "runs": [
            {
                "run_id": r.id,
                "thread_id": r.thread_id,
                "skill": r.skill,
                "status": r.status,
                "charged": r.charged,
                "created_at": r.created_at.isoformat() + "Z",
                "finished_at": r.finished_at.isoformat() + "Z"
                if r.finished_at
                else None,
                "total_tokens": r.total_tokens,
                "model": r.model_name,
                "has_result": bool(r.result_md or r.file_path),
            }
            for r in result.scalars()
        ]
    }


@runs_router.get("/{run_id}")
async def get_run(
    run_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    run = await session.get(Run, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "run_id": run.id,
        "thread_id": run.thread_id,
        "skill": run.skill,
        "status": run.status,
        "charged": run.charged,
        "result_md": run.result_md,
        "receipt": {
            "model": run.model_name,
            "total_tokens": run.total_tokens,
            "created_at": run.created_at.isoformat() + "Z",
            "finished_at": run.finished_at.isoformat() + "Z"
            if run.finished_at
            else None,
        },
    }
