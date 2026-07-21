# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import os
from datetime import timedelta

import pytest
import pytest_asyncio
from fastapi import HTTPException

os.environ.setdefault("PLATFORM_DATABASE_URL", "sqlite+aiosqlite:///./test_platform.db")

from src.platform import runtime  # noqa: E402
from src.platform.auth import activate_or_login, renew  # noqa: E402
from src.platform.db import SessionLocal, engine, init_db  # noqa: E402
from src.platform.models import (  # noqa: E402
    ActivationCode,
    Base,
    ModelEntry,
    Plan,
    Run,
    User,
    generate_card_code,
    utcnow,
)


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    runtime._handles.clear()
    runtime._active_users.clear()
    yield


async def make_card(plan_uses=3, valid_days=7, token_reserve=0) -> str:
    async with SessionLocal() as session:
        model = ModelEntry(
            display_name="测试模型",
            model_name="test-model",
            base_url="http://localhost:9999/v1",
            api_key_env="TEST_KEY",
            provider="test",
        )
        plan = Plan(
            name="test",
            total_uses=plan_uses,
            valid_minutes=valid_days * 24 * 60,
            token_reserve=token_reserve,
        )
        session.add_all([model, plan])
        await session.flush()
        code = generate_card_code()
        session.add(ActivationCode(code=code, plan_id=plan.id, model_id=model.id))
        await session.commit()
        return code


@pytest.mark.asyncio
async def test_activate_then_login_kicks_old_session():
    code = await make_card()
    async with SessionLocal() as session:
        user, is_new = await activate_or_login(session, code)
        assert is_new and user.remaining_uses == 3
        first_session = user.session_id
    async with SessionLocal() as session:
        user2, is_new2 = await activate_or_login(session, code)
        assert not is_new2 and user2.id == user.id
        assert user2.session_id != first_session  # 旧会话被踢


@pytest.mark.asyncio
async def test_invalid_code_rejected():
    async with SessionLocal() as session:
        with pytest.raises(HTTPException) as e:
            await activate_or_login(session, "AAAAAA-BBBBBB-CCCCCC-DDDDDD")
        assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_renew_stacks_uses_and_extends_expiry():
    code1 = await make_card(plan_uses=3, valid_days=7)
    code2 = await make_card(plan_uses=20, valid_days=30)
    async with SessionLocal() as session:
        user, _ = await activate_or_login(session, code1)
        old_expiry = user.expires_at
        user = await renew(session, user, code2)
        assert user.remaining_uses == 23  # 叠加而非覆盖
        assert user.expires_at > old_expiry
    async with SessionLocal() as session:
        with pytest.raises(HTTPException):  # 已用过的卡不能再充
            user = await session.get(User, user.id)
            await renew(session, user, code2)


@pytest.mark.asyncio
async def test_precheck_rejects_exhausted_and_expired():
    code = await make_card(plan_uses=1)
    async with SessionLocal() as session:
        user, _ = await activate_or_login(session, code)
        uid = user.id
    # 次数耗尽
    async with SessionLocal() as session:
        u = await session.get(User, uid)
        u.remaining_uses = 0
        await session.commit()
    with pytest.raises(HTTPException) as e:
        await runtime.precheck_and_create_run(uid, "t1", "research")
    assert e.value.status_code == 402
    # 过期
    async with SessionLocal() as session:
        u = await session.get(User, uid)
        u.remaining_uses = 5
        u.expires_at = utcnow() - timedelta(days=1)
        await session.commit()
    with pytest.raises(HTTPException) as e:
        await runtime.precheck_and_create_run(uid, "t2", "research")
    assert e.value.status_code == 402


@pytest.mark.asyncio
async def test_thread_ownership_enforced():
    code_a = await make_card()
    code_b = await make_card()
    async with SessionLocal() as session:
        user_a, _ = await activate_or_login(session, code_a)
        user_b, _ = await activate_or_login(session, code_b)
    handle, _ = await runtime.precheck_and_create_run(user_a.id, "shared", "research")
    await runtime.finish_run_now(handle, user_a.id, runtime.TokenMeter(0), False)
    with pytest.raises(HTTPException) as e:
        await runtime.precheck_and_create_run(user_b.id, "shared", "research")
    assert e.value.status_code == 403  # B 不能用 A 的 thread


class _StubChunk:
    """模拟 reporter 的 AIMessageChunk."""

    def __init__(self, content):
        self.content = content
        self.id = "stub"
        self.response_metadata = {}
        self.tool_calls = []
        self.tool_call_chunks = []


class _StubGraph:
    def __init__(self, report="最终研究报告", fail=False):
        self.report = report
        self.fail = fail

    async def astream(self, input_, config=None, **kwargs):
        from langchain_core.messages import AIMessageChunk

        if self.fail:
            raise RuntimeError("upstream 500")
        chunk = AIMessageChunk(content=self.report)
        yield (("reporter:xyz",), "messages", (chunk, {}))


@pytest.mark.asyncio
async def test_success_charges_one_use():
    code = await make_card(plan_uses=3)
    async with SessionLocal() as session:
        user, _ = await activate_or_login(session, code)
    handle, conf = await runtime.precheck_and_create_run(user.id, "t-ok", "research")
    await runtime._execute(_StubGraph(), handle, conf, user.id, {}, {})
    async with SessionLocal() as session:
        u = await session.get(User, user.id)
        assert u.remaining_uses == 2  # 成功扣一次
        run = await session.get(Run, handle.run_id)
        assert run.status == Run.STATUS_SUCCEEDED
        assert run.charged and run.result_md == "最终研究报告"
    assert any("run_complete" in e for e in handle.backlog)


@pytest.mark.asyncio
async def test_failure_does_not_charge():
    code = await make_card(plan_uses=3)
    async with SessionLocal() as session:
        user, _ = await activate_or_login(session, code)
    handle, conf = await runtime.precheck_and_create_run(user.id, "t-fail", "research")
    await runtime._execute(_StubGraph(fail=True), handle, conf, user.id, {}, {})
    async with SessionLocal() as session:
        u = await session.get(User, user.id)
        assert u.remaining_uses == 3  # 失败不扣次
        run = await session.get(Run, handle.run_id)
        assert run.status == Run.STATUS_FAILED and not run.charged
    assert any("run_error" in e for e in handle.backlog)
    assert any("未扣除次数" in e for e in handle.backlog)


@pytest.mark.asyncio
async def test_per_user_single_concurrent_run():
    code = await make_card()
    async with SessionLocal() as session:
        user, _ = await activate_or_login(session, code)
    handle, _ = await runtime.precheck_and_create_run(user.id, "t-c1", "research")
    with pytest.raises(HTTPException) as e:
        await runtime.precheck_and_create_run(user.id, "t-c2", "research")
    assert e.value.status_code == 409
    await runtime.finish_run_now(handle, user.id, runtime.TokenMeter(0), False)
    # 结束后可再次发起
    handle2, _ = await runtime.precheck_and_create_run(user.id, "t-c3", "research")
    assert handle2 is not None


@pytest.mark.asyncio
async def test_subscriber_replay_after_disconnect():
    code = await make_card()
    async with SessionLocal() as session:
        user, _ = await activate_or_login(session, code)
    handle, conf = await runtime.precheck_and_create_run(
        user.id, "t-replay", "research"
    )
    await runtime._execute(
        _StubGraph(report="离线也能拿到"), handle, conf, user.id, {}, {}
    )
    # 任务结束后新订阅者（模拟断线重连）仍能回放全部事件
    q = handle.subscribe()
    events = []
    while True:
        item = q.get_nowait()
        if item is None:
            break
        events.append(item)
    assert any("离线也能拿到" in e for e in events)
    assert any("run_complete" in e for e in events)


@pytest.mark.asyncio
async def test_token_reserve_fuse_blocks_when_exhausted():
    code = await make_card(token_reserve=1000)
    async with SessionLocal() as session:
        user, _ = await activate_or_login(session, code)
        uid = user.id
    async with SessionLocal() as session:
        u = await session.get(User, uid)
        u.token_reserve = -5
        await session.commit()
    with pytest.raises(HTTPException) as e:
        await runtime.precheck_and_create_run(uid, "t-fuse", "research")
    assert e.value.status_code == 402
