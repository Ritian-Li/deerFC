# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import base64
import logging
import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse

from src.graph.builder import build_graph_with_persistence
from src.llms.llm import current_model_conf
from src.platform import runtime
from src.platform.admin import require_admin
from src.platform.admin import router as admin_router
from src.platform.auth import get_current_user
from src.platform.db import get_session, init_db
from src.platform.models import Run, Thread, User
from src.platform.routes import auth_router, runs_router
from src.platform.runtime import (
    TASK_TOKEN_CAP,
    TokenMeter,
    finish_run_now,
    get_handle,
    precheck_and_create_run,
    spawn_run,
)
from src.server.chat_request import (
    ChatRequest,
    GeneratePodcastRequest,
    GeneratePPTRequest,
    GenerateProseRequest,
    SkillPromptRequest,
    TTSRequest,
)
from src.server.mcp_request import MCPServerMetadataRequest, MCPServerMetadataResponse
from src.server.mcp_utils import load_mcp_tools
from src.tools import VolcengineTTS
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

graph = None

# 服务端硬上限：不信任前端传参，防止参数拉满薅 token
MAX_STEP_NUM_CAP = int(os.getenv("PLATFORM_MAX_STEP_NUM", "3"))
MAX_SEARCH_RESULTS_CAP = int(os.getenv("PLATFORM_MAX_SEARCH_RESULTS", "3"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    await init_db()
    graph = await build_graph_with_persistence()
    logger.info("platform initialized, graph compiled with durable checkpointer")
    yield


app = FastAPI(
    title="DeerFlow API",
    description="API for Deer",
    version="0.1.0",
    lifespan=lifespan,
)

_allowed_origins = [
    o.strip()
    for o in os.getenv("PLATFORM_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(runs_router)
app.include_router(admin_router)


async def _stream_from_handle(handle: runtime.RunHandle):
    queue = handle.subscribe()
    while True:
        item = await queue.get()
        if item is None:
            break
        yield item


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, user: User = Depends(get_current_user)):
    thread_id = request.thread_id
    if thread_id == "__default__":
        thread_id = str(uuid4())
    handle, model_conf = await precheck_and_create_run(user.id, thread_id, "research")
    input_ = {
        "messages": request.model_dump()["messages"],
        "plan_iterations": 0,
        "final_report": "",
        "current_plan": None,
        "observations": [],
        # 强制自动接受计划：C 端小白场景下计划确认只产生流失
        "auto_accepted_plan": True,
        "enable_background_investigation": request.enable_background_investigation,
    }
    config = {
        "thread_id": thread_id,
        "max_plan_iterations": 1,
        "max_step_num": min(request.max_step_num or MAX_STEP_NUM_CAP, MAX_STEP_NUM_CAP),
        "max_search_results": min(
            request.max_search_results or MAX_SEARCH_RESULTS_CAP,
            MAX_SEARCH_RESULTS_CAP,
        ),
        # C 端不允许自带 MCP 工具（任意命令执行入口）
        "mcp_settings": None,
    }
    spawn_run(graph, handle, model_conf, user.id, input_, config)
    return StreamingResponse(
        _stream_from_handle(handle), media_type="text/event-stream"
    )


@app.get("/api/chat/stream/{thread_id}")
async def chat_stream_reattach(
    thread_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """断线重连：回放 backlog 并续接直播；任务本身与连接无关，断了照跑."""
    thread = await session.get(Thread, thread_id)
    if thread is None or thread.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    handle = get_handle(thread_id)
    if handle is None:
        raise HTTPException(
            status_code=404, detail="任务已结束，请在任务记录中查看结果"
        )
    return StreamingResponse(
        _stream_from_handle(handle), media_type="text/event-stream"
    )


@app.get("/api/runs/{run_id}/file")
async def download_run_file(
    run_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    run = await session.get(Run, run_id)
    if run is None or run.user_id != user.id or not run.file_path:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not os.path.exists(run.file_path):
        raise HTTPException(status_code=404, detail="文件已过期，请重新生成")
    return FileResponse(run.file_path, filename=os.path.basename(run.file_path))


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest, user: User = Depends(get_current_user)):
    """Convert text to speech using volcengine TTS API."""
    try:
        app_id = os.getenv("VOLCENGINE_TTS_APPID", "")
        if not app_id:
            raise HTTPException(
                status_code=400, detail="VOLCENGINE_TTS_APPID is not set"
            )
        access_token = os.getenv("VOLCENGINE_TTS_ACCESS_TOKEN", "")
        if not access_token:
            raise HTTPException(
                status_code=400, detail="VOLCENGINE_TTS_ACCESS_TOKEN is not set"
            )
        cluster = os.getenv("VOLCENGINE_TTS_CLUSTER", "volcano_tts")
        voice_type = os.getenv("VOLCENGINE_TTS_VOICE_TYPE", "BV700_V2_streaming")

        tts_client = VolcengineTTS(
            appid=app_id,
            access_token=access_token,
            cluster=cluster,
            voice_type=voice_type,
        )
        result = await asyncio.to_thread(
            tts_client.text_to_speech,
            text=request.text[:1024],
            encoding=request.encoding,
            speed_ratio=request.speed_ratio,
            volume_ratio=request.volume_ratio,
            pitch_ratio=request.pitch_ratio,
            text_type=request.text_type,
            with_frontend=request.with_frontend,
            frontend_type=request.frontend_type,
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=str(result["error"]))

        audio_data = base64.b64decode(result["audio_data"])
        return Response(
            content=audio_data,
            media_type=f"audio/{request.encoding}",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=tts_output.{request.encoding}"
                )
            },
        )
    except Exception as e:
        logger.exception(f"Error in TTS endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_sync_skill(user: User, skill: str, invoke):
    """PPT/播客等同步图的统一执行：预检 → 计量 → 成功才扣次."""
    handle, model_conf = await precheck_and_create_run(
        user.id, f"{skill}-{uuid4()}", skill
    )
    current_model_conf.set(model_conf)
    meter = TokenMeter(cap=TASK_TOKEN_CAP)
    try:
        final_state = await asyncio.to_thread(invoke, {"callbacks": [meter]})
    except Exception as e:
        await finish_run_now(handle, user.id, meter, False, error_detail=repr(e))
        logger.exception("%s generation failed", skill)
        raise HTTPException(status_code=500, detail="生成失败，未扣除次数，请重试")
    return handle, meter, final_state


FILES_DIR = os.getenv("PLATFORM_FILES_DIR", "./generated_files")


def _persist_artifact(user_id: int, run_id: int, filename: str, data: bytes) -> str:
    """产物落盘：之后走 /api/runs/{id}/file 重复下载，避免重复生成烧 token."""
    user_dir = os.path.join(FILES_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    path = os.path.join(user_dir, f"{run_id}-{filename}")
    with open(path, "wb") as f:
        f.write(data)
    return path


@app.post("/api/podcast/generate")
async def generate_podcast(
    request: GeneratePodcastRequest, user: User = Depends(get_current_user)
):
    from src.podcast.graph.builder import build_graph as build_podcast_graph

    workflow = build_podcast_graph()
    handle, meter, final_state = await _run_sync_skill(
        user,
        "podcast",
        lambda config: workflow.invoke({"input": request.content}, config=config),
    )
    audio_bytes = final_state["output"]
    file_path = _persist_artifact(user.id, handle.run_id, "podcast.mp3", audio_bytes)
    await finish_run_now(handle, user.id, meter, True, file_path=file_path)
    return Response(content=audio_bytes, media_type="audio/mp3")


@app.post("/api/ppt/generate")
async def generate_ppt(
    request: GeneratePPTRequest, user: User = Depends(get_current_user)
):
    from src.ppt.graph.builder import build_graph as build_ppt_graph

    workflow = build_ppt_graph()
    handle, meter, final_state = await _run_sync_skill(
        user,
        "ppt",
        lambda config: workflow.invoke({"input": request.content}, config=config),
    )
    generated_file_path = final_state["generated_file_path"]
    with open(generated_file_path, "rb") as f:
        ppt_bytes = f.read()
    # ppt_generator 写在临时目录，统一挪进产物目录便于清理与配额管理
    file_path = _persist_artifact(user.id, handle.run_id, "slides.pptx", ppt_bytes)
    await finish_run_now(handle, user.id, meter, True, file_path=file_path)
    return Response(
        content=ppt_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


_DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


async def _run_docx_skill(user: User, skill: str, generate, filename: str):
    """教育类 skill（组卷/教案）：LLM 生成结构化内容 → Word → 落盘 → 成功才扣次."""
    handle, meter, final_state = await _run_sync_skill(user, skill, generate)
    generated_file_path = final_state["generated_file_path"]
    with open(generated_file_path, "rb") as f:
        docx_bytes = f.read()
    os.remove(generated_file_path)
    file_path = _persist_artifact(user.id, handle.run_id, filename, docx_bytes)
    await finish_run_now(handle, user.id, meter, True, file_path=file_path)
    return Response(
        content=docx_bytes,
        media_type=_DOCX_MEDIA,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/exam/generate")
async def generate_exam_endpoint(
    request: SkillPromptRequest, user: User = Depends(get_current_user)
):
    """智能组卷：一句话需求 → 试卷 Word（题目+答案+解析）."""
    from src.skills import generate_exam

    return await _run_docx_skill(
        user,
        "exam",
        lambda config: generate_exam(request.prompt, config),
        "exam.docx",
    )


@app.post("/api/lesson/generate")
async def generate_lesson_endpoint(
    request: SkillPromptRequest, user: User = Depends(get_current_user)
):
    """教案生成：一句话需求 → 教案 Word（目标/重难点/过程/板书/作业）."""
    from src.skills import generate_lesson

    return await _run_docx_skill(
        user,
        "lesson",
        lambda config: generate_lesson(request.prompt, config),
        "lesson.docx",
    )


@app.post("/api/prose/generate")
async def generate_prose(
    request: GenerateProseRequest, user: User = Depends(get_current_user)
):
    from src.prose.graph.builder import build_graph as build_prose_graph

    handle, model_conf = await precheck_and_create_run(
        user.id, f"prose-{uuid4()}", "prose"
    )
    current_model_conf.set(model_conf)
    meter = TokenMeter(cap=TASK_TOKEN_CAP)
    workflow = build_prose_graph()

    async def stream():
        parts = []
        try:
            events = workflow.astream(
                {
                    "content": request.prompt,
                    "option": request.option,
                    "command": request.command,
                },
                config={"callbacks": [meter]},
                stream_mode="messages",
                subgraphs=True,
            )
            async for _, event in events:
                parts.append(event[0].content)
                yield f"data: {event[0].content}\n\n"
        except Exception as e:
            await finish_run_now(handle, user.id, meter, False, error_detail=repr(e))
            logger.exception("prose generation failed")
            yield "data: [ERROR] 生成失败，未扣除次数，请重试\n\n"
            return
        await finish_run_now(handle, user.id, meter, True, result_md="".join(parts))

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post(
    "/api/mcp/server/metadata",
    response_model=MCPServerMetadataResponse,
    dependencies=[Depends(require_admin)],
)
async def mcp_server_metadata(request: MCPServerMetadataRequest):
    """Get information about an MCP server. Admin only: MCP 配置等于任意命令执行."""
    try:
        timeout = 300
        if request.timeout_seconds is not None:
            timeout = request.timeout_seconds
        tools = await load_mcp_tools(
            server_type=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            timeout_seconds=timeout,
        )
        response = MCPServerMetadataResponse(
            transport=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            tools=tools,
        )
        return response
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.exception(f"Error in MCP server metadata endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        raise
