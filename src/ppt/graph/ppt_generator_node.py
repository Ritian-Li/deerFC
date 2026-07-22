# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import subprocess
import uuid

from src.ppt.graph.state import PPTState

logger = logging.getLogger(__name__)


def ppt_generator_node(state: PPTState):
    logger.info("Generating ppt file...")
    # use marp cli to generate ppt file
    # https://github.com/marp-team/marp-cli?tab=readme-ov-file
    generated_file_path = os.path.join(
        os.getcwd(), f"generated_ppt_{uuid.uuid4()}.pptx"
    )
    # marp 导出 pptx 需要 chrome；--allow-local-files 允许本地资源，
    # 显式设置 --browser-path（root 下 chrome-headless-shell 需要）
    cmd = ["marp", state["ppt_file_path"], "--pptx", "-o", generated_file_path]
    chrome_path = os.getenv("CHROME_PATH", "")
    if chrome_path:
        cmd += ["--browser-path", chrome_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
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
