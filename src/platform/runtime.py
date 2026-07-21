# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import json
import logging
import os
from typing import Any, List, Optional, cast

from fastapi import HTTPException
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessageChunk, BaseMessage, ToolMessage
from sqlalchemy import func, select

from src.llms.llm import current_model_conf
from src.platform.db import SessionLocal
from src.platform.models import ModelEntry, Run, Thread, User, utcnow

logger = logging.getLogger(__name__)

TASK_TOKEN_CAP = int(os.getenv("PLATFORM_TASK_TOKEN_CAP", "500000"))
DAILY_TOKEN_BUDGET = int(os.getenv("PLATFORM_DAILY_TOKEN_BUDGET", "0"))  # 0 = 不限
MAX_CONCURRENT_RUNS = int(os.getenv("PLATFORM_MAX_CONCURRENT_RUNS", "3"))

_END_OF_STREAM = None


class TokenCapExceeded(Exception):
    pass


class TokenMeter(BaseCallbackHandler):
    """聚合一次 run 内所有 LLM 调用的 token 用量；超过单任务熔断上限时中止 run."""

    raise_error = True

    def __init__(self, cap: int):
        self.cap = cap
        self.prompt_tokens = 0
        self.completion_tokens = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def on_llm_end(self, response, **kwargs):
        found = False
        for gens in response.generations:
            for gen in gens:
                usage = getattr(getattr(gen, "message", None), "usage_metadata", None)
                if usage:
                    self.prompt_tokens += usage.get("input_tokens", 0)
                    self.completion_tokens += usage.get("output_tokens", 0)
                    found = True
        if not found and response.llm_output:
            usage = response.llm_output.get("token_usage") or {}
            self.prompt_tokens += usage.get("prompt_tokens", 0)
            self.completion_tokens += usage.get("completion_tokens", 0)
        if self.cap and self.total_tokens > self.cap:
            raise TokenCapExceeded(
                f"task token cap exceeded: {self.total_tokens} > {self.cap}"
            )


class RunHandle:
    """一次 run 的事件总线：执行器往里发，任意数量的 SSE 观察者订阅（断线可重连回放）."""

    def __init__(self, run_id: int, thread_id: str):
        self.run_id = run_id
        self.thread_id = thread_id
        self.backlog: List[str] = []
        self.subscribers: List[asyncio.Queue] = []
        self.done = False

    def publish(self, event: str) -> None:
        self.backlog.append(event)
        for q in self.subscribers:
            q.put_nowait(event)

    def finish(self) -> None:
        self.done = True
        for q in self.subscribers:
            q.put_nowait(_END_OF_STREAM)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        for event in self.backlog:
            q.put_nowait(event)
        if self.done:
            q.put_nowait(_END_OF_STREAM)
        else:
            self.subscribers.append(q)
        return q


_handles: dict[str, RunHandle] = {}  # thread_id -> latest run handle
_active_users: set[int] = set()


def get_handle(thread_id: str) -> Optional[RunHandle]:
    return _handles.get(thread_id)


def make_event(event_type: str, data: dict[str, Any]) -> str:
    if data.get("content") == "":
        data.pop("content")
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _daily_tokens_used(session) -> int:
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.coalesce(func.sum(Run.total_tokens), 0)).where(
            Run.created_at >= today
        )
    )
    return result.scalar_one()


async def _alert(message: str) -> None:
    logger.error("PLATFORM ALERT: %s", message)
    webhook = os.getenv("PLATFORM_ALERT_WEBHOOK", "")
    if webhook:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(webhook, json={"text": message})
        except Exception:
            logger.exception("failed to deliver alert webhook")


async def precheck_and_create_run(
    user_id: int, thread_id: str, skill: str
) -> tuple[RunHandle, dict]:
    """入口预检（次数/有效期/隐藏熔断/并发/每日预算），通过则登记 run.

    返回 (handle, model_conf)。所有拒绝路径都不扣次数。
    """
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None or user.banned:
            raise HTTPException(status_code=403, detail="账号不可用，请联系卖家")
        if user.expires_at < utcnow():
            raise HTTPException(
                status_code=402, detail="卡密已过有效期，请联系卖家续费"
            )
        if user.remaining_uses <= 0:
            raise HTTPException(
                status_code=402, detail="剩余次数已用完，请联系卖家续费"
            )
        # 隐藏 token 熔断：激活时若配了 reserve（>0 表示启用），耗尽即拦截
        code_has_reserve = user.token_reserve != 0
        if code_has_reserve and user.token_reserve <= 0:
            raise HTTPException(
                status_code=402, detail="当前卡密服务额度已用完，请联系卖家"
            )
        if DAILY_TOKEN_BUDGET:
            used = await _daily_tokens_used(session)
            if used >= DAILY_TOKEN_BUDGET:
                await _alert(f"每日 token 预算已耗尽（{used}），新任务已熔断")
                raise HTTPException(
                    status_code=503, detail="今日服务繁忙，请明天再试（未扣除次数）"
                )

        thread = await session.get(Thread, thread_id)
        if thread is None:
            session.add(Thread(thread_id=thread_id, user_id=user_id))
        elif thread.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权访问该会话")

        if user_id in _active_users:
            raise HTTPException(
                status_code=409, detail="您已有任务进行中，请等它完成后再试"
            )
        running = sum(1 for h in _handles.values() if not h.done)
        if running >= MAX_CONCURRENT_RUNS:
            raise HTTPException(
                status_code=503,
                detail="当前使用人数较多，请几分钟后再试（未扣除次数）",
            )

        model = await session.get(ModelEntry, user.model_id)
        if model is None or not model.active:
            raise HTTPException(
                status_code=503, detail="当前模型维护中，请稍后再试或联系卖家"
            )

        run = Run(
            user_id=user_id,
            thread_id=thread_id,
            skill=skill,
            model_name=model.model_name,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

    handle = RunHandle(run.id, thread_id)
    _handles[thread_id] = handle
    _active_users.add(user_id)
    model_conf = {
        "model": model.model_name,
        "base_url": model.base_url,
        "api_key_env": model.api_key_env,
        "display_name": model.display_name,
        "provider": model.provider,
    }
    return handle, model_conf


async def finish_run_now(
    handle: RunHandle,
    user_id: int,
    meter: "TokenMeter",
    success: bool,
    result_md: str = "",
    file_path: str = "",
    error_detail: str = "",
) -> int:
    """同步型 skill（PPT/播客/改写）的结算：成功才扣次，返回剩余次数."""
    remaining = -1
    try:
        async with SessionLocal() as session:
            run = await session.get(Run, handle.run_id)
            user = await session.get(User, user_id)
            run.prompt_tokens = meter.prompt_tokens
            run.completion_tokens = meter.completion_tokens
            run.total_tokens = meter.total_tokens
            run.finished_at = utcnow()
            run.error = error_detail
            if success:
                run.status = Run.STATUS_SUCCEEDED
                run.result_md = result_md
                run.file_path = file_path
                run.charged = True
                user.remaining_uses -= 1
                if user.token_reserve != 0:
                    user.token_reserve -= meter.total_tokens
            else:
                run.status = Run.STATUS_FAILED
            remaining = user.remaining_uses
            await session.commit()
    except Exception:
        logger.exception("failed to settle sync run %s", handle.run_id)
    _active_users.discard(user_id)
    handle.finish()
    if _handles.get(handle.thread_id) is handle:
        _handles.pop(handle.thread_id, None)
    return remaining


def spawn_run(
    graph,
    handle: RunHandle,
    model_conf: dict,
    user_id: int,
    input_: Any,
    config: dict,
) -> None:
    asyncio.create_task(
        _execute(graph, handle, model_conf, user_id, input_, config),
        name=f"run-{handle.run_id}",
    )


async def _execute(
    graph,
    handle: RunHandle,
    model_conf: dict,
    user_id: int,
    input_: Any,
    config: dict,
) -> None:
    """驱动 graph 到终态；与 HTTP 连接完全解耦，断线任务照跑，产物落库."""
    current_model_conf.set(model_conf)
    meter = TokenMeter(cap=TASK_TOKEN_CAP)
    config = {**config, "callbacks": [meter]}
    started = utcnow()
    report_parts: List[str] = []
    error_public = ""
    error_detail = ""
    try:
        async for agent, _, event_data in graph.astream(
            input_, config=config, stream_mode=["messages", "updates"], subgraphs=True
        ):
            if isinstance(event_data, dict):
                # auto_accepted_plan 已强制开启，正常不会出现 interrupt；出现即按失败收尾
                if "__interrupt__" in event_data:
                    raise RuntimeError("unexpected interrupt in auto-accept mode")
                continue
            message_chunk, _meta = cast(tuple[BaseMessage, dict[str, Any]], event_data)
            agent_name = agent[0].split(":")[0] if agent else "unknown"
            event_stream_message: dict[str, Any] = {
                "thread_id": handle.thread_id,
                "agent": agent_name,
                "id": message_chunk.id,
                "role": "assistant",
                "content": message_chunk.content,
            }
            if message_chunk.response_metadata.get("finish_reason"):
                event_stream_message["finish_reason"] = (
                    message_chunk.response_metadata.get("finish_reason")
                )
            if isinstance(message_chunk, ToolMessage):
                event_stream_message["tool_call_id"] = message_chunk.tool_call_id
                handle.publish(make_event("tool_call_result", event_stream_message))
            elif isinstance(message_chunk, AIMessageChunk):
                if agent_name == "reporter" and isinstance(message_chunk.content, str):
                    report_parts.append(message_chunk.content)
                if message_chunk.tool_calls:
                    event_stream_message["tool_calls"] = message_chunk.tool_calls
                    event_stream_message["tool_call_chunks"] = (
                        message_chunk.tool_call_chunks
                    )
                    handle.publish(make_event("tool_calls", event_stream_message))
                elif message_chunk.tool_call_chunks:
                    event_stream_message["tool_call_chunks"] = (
                        message_chunk.tool_call_chunks
                    )
                    handle.publish(make_event("tool_call_chunks", event_stream_message))
                else:
                    handle.publish(make_event("message_chunk", event_stream_message))
    except TokenCapExceeded:
        error_public = "本次任务过于复杂已中止，未扣除次数，请拆分问题后重试"
        error_detail = f"token cap {TASK_TOKEN_CAP} exceeded"
    except Exception as e:
        # LangChain 会把 callback 抛出的熔断包一层，这里再识别一次
        if "token cap exceeded" in str(e):
            error_public = "本次任务过于复杂已中止，未扣除次数，请拆分问题后重试"
        else:
            error_public = "本次任务执行失败，未扣除次数，请重试"
        error_detail = repr(e)
        logger.exception("run %s failed", handle.run_id)

    report = "".join(report_parts).strip()
    succeeded = not error_public and bool(report)
    # 无报告也无异常 = 闲聊类对话（coordinator 直接回复），完成但不计次
    chitchat = not error_public and not report
    duration_ms = int((utcnow() - started).total_seconds() * 1000)

    try:
        async with SessionLocal() as session:
            run = await session.get(Run, handle.run_id)
            user = await session.get(User, user_id)
            run.prompt_tokens = meter.prompt_tokens
            run.completion_tokens = meter.completion_tokens
            run.total_tokens = meter.total_tokens
            run.finished_at = utcnow()
            run.error = error_detail
            if succeeded:
                run.status = Run.STATUS_SUCCEEDED
                run.result_md = report
                run.charged = True
                user.remaining_uses -= 1
                if user.token_reserve != 0:
                    user.token_reserve -= meter.total_tokens
            elif chitchat:
                run.status = Run.STATUS_SUCCEEDED
            else:
                run.status = Run.STATUS_FAILED
            remaining = user.remaining_uses if user else 0
            await session.commit()
    except Exception:
        logger.exception("failed to settle run %s", handle.run_id)
        remaining = -1

    if succeeded:
        handle.publish(
            make_event(
                "run_complete",
                {
                    "thread_id": handle.thread_id,
                    "run_id": handle.run_id,
                    "receipt": {
                        "model": model_conf["display_name"],
                        "provider": model_conf["provider"],
                        "total_tokens": meter.total_tokens,
                        "duration_ms": duration_ms,
                    },
                    "remaining_uses": remaining,
                },
            )
        )
    elif error_public:
        handle.publish(
            make_event(
                "run_error",
                {
                    "thread_id": handle.thread_id,
                    "run_id": handle.run_id,
                    "content": error_public,
                    "remaining_uses": remaining,
                },
            )
        )
    else:
        handle.publish(
            make_event(
                "run_complete",
                {
                    "thread_id": handle.thread_id,
                    "run_id": handle.run_id,
                    "charged": False,
                    "remaining_uses": remaining,
                },
            )
        )

    _active_users.discard(user_id)
    handle.finish()

    def _cleanup():
        if _handles.get(handle.thread_id) is handle:
            _handles.pop(handle.thread_id, None)

    # 保留 10 分钟供断线重连回放，之后清理
    asyncio.get_running_loop().call_later(600, _cleanup)
