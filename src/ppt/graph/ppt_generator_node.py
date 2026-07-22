# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import re
import subprocess
import uuid

from src.ppt.graph.state import PPTState

logger = logging.getLogger(__name__)

# markdown 图片语法（含 marp 的 ![bg](url) 背景图指令）
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
# emoji 及杂项符号：chrome-headless-shell 渲染彩色 emoji 会挂起直到 marp 超时
_EMOJI_RE = re.compile(
    "[\U0001f000-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff"
    "\U00002190-\U000021ff\U00002b00-\U00002bff️‍]"
)


def _sanitize_markdown(md_path: str) -> None:
    """marp 前清洗：去掉外链图片（出网受限时 chrome 拉图挂起）与 emoji
    （chrome-headless-shell 渲染彩色 emoji 会挂起到超时）。输入只有主题文字，去掉无损内容."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    cleaned = _EMOJI_RE.sub("", _IMAGE_RE.sub("", content))
    if cleaned != content:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(cleaned)


def ppt_generator_node(state: PPTState):
    logger.info("Generating ppt file...")
    # use marp cli to generate ppt file
    # https://github.com/marp-team/marp-cli?tab=readme-ov-file
    _sanitize_markdown(state["ppt_file_path"])
    generated_file_path = os.path.join(
        os.getcwd(), f"generated_ppt_{uuid.uuid4()}.pptx"
    )
    # marp 导出 pptx 需要 chrome；--allow-local-files 允许本地资源，
    # 显式设置 --browser-path（root 下 chrome-headless-shell 需要）
    cmd = ["marp", state["ppt_file_path"], "--pptx", "-o", generated_file_path]
    chrome_path = os.getenv("CHROME_PATH", "")
    if chrome_path:
        cmd += ["--browser-path", chrome_path]
    # start_new_session：把 marp+chrome 放进独立会话，隔离 uvicorn/asyncio 的
    # SIGCHLD 处理——否则从服务进程内 spawn 时 puppeteer 连不上 chrome 会 30s 超时
    result = subprocess.run(cmd, capture_output=True, text=True, start_new_session=True)
    # remove the temp file
    if os.path.exists(state["ppt_file_path"]):
        os.remove(state["ppt_file_path"])
    if result.returncode != 0 or not os.path.exists(generated_file_path):
        logger.error(
            "marp failed (code=%s): %s",
            result.returncode,
            (result.stderr or result.stdout or "no output").strip(),
        )
        raise RuntimeError(f"PPT 生成失败：marp 转换出错 - {result.stderr[:300]}")
    logger.info(f"generated_file_path: {generated_file_path}")
    return {"generated_file_path": generated_file_path}
