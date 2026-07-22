# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langchain.schema import HumanMessage, SystemMessage

from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.skills.common import parse_json_response
from src.skills.xlsx_export import build_xlsx

SHEET_SYSTEM_PROMPT = """你是一位擅长把信息整理成规范表格的行政/数据助理。根据用户要求生成一份可直接使用的 Excel 表格。

要求：
- 准确理解用户要的表格类型、行列结构与数据；用户没给的信息用「【待补充】」占位，不要编造具体数据。
- 表头命名规范、粒度一致；每行数据完整对齐表头；需要合计/汇总时单独成行。
- 数字直接给数值（不带单位混入），单位写进表头（如「单价（元）」）。

只输出一个 JSON 对象，不要有任何多余文字或 markdown 围栏，格式如下：
{
  "title": "表格标题",
  "sheets": [
    {
      "name": "工作表名（≤31字符）",
      "headers": ["列1", "列2"],
      "rows": [["值", "值"], ["值", "值"]],
      "note": "使用说明，可留空"
    }
  ]
}"""


def generate_spreadsheet(prompt: str, config: dict, preset_text: str = "") -> dict:
    """一句话需求 -> 结构化表格 -> xlsx 文件。

    子能力（课程表/排班/预算/进度）以 preset_text 注入结构约束。
    """
    system = SHEET_SYSTEM_PROMPT
    if preset_text:
        system += f"\n\n【本表格类型约束】{preset_text}\n用户明确指定的要求优先于上述约束。"
    llm = get_llm_by_type(AGENT_LLM_MAP.get("reporter", "basic"))
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=prompt),
    ]
    resp = llm.invoke(messages, config=config)
    data = parse_json_response(resp.content)
    path = build_xlsx(data)
    return {"generated_file_path": path, "title": data.get("title", "表格")}
