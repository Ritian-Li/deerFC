# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import re

from json_repair import repair_json


def parse_json_response(content: str) -> dict:
    """从 LLM 回复中稳健地解析 JSON：去掉 ```json 围栏、修复常见格式错误."""
    if not isinstance(content, str):
        content = str(content)
    text = content.strip()
    # 去掉 markdown 代码围栏
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return json.loads(repair_json(text))
