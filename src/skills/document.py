# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langchain.schema import HumanMessage, SystemMessage

from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.skills.common import parse_json_response
from src.skills.docx_export import build_sections_docx

DOC_SYSTEM_PROMPT = """你是一位文笔扎实的办公文书写手。根据用户要求撰写一份规范、可直接使用的办公文档。

要求：
- 准确理解用户的文档类型与要素（人物/时间/事项等）；用户没给的信息用「【待补充：××】」占位，不要编造具体人名、日期、数据。
- 结构清晰、小节划分合理；语言得体，符合该文档类型的通用行文习惯。
- 涉及数字或结论时基于用户给的材料，不虚构。

只输出一个 JSON 对象，不要有任何多余文字或 markdown 围栏，格式如下：
{
  "title": "文档标题",
  "meta": "副标题/署名/日期行，可留空",
  "sections": [
    {"heading": "一、小节标题", "content": "小节正文，可用\\n分段"},
    {"heading": "二、小节标题", "content": "...",
     "chart": {"type": "bar", "title": "图表标题",
               "categories": ["类目"], "series": [{"name": "系列名", "values": [1, 2]}]}}
  ]
}

chart 为可选字段：仅当该小节的数据存在对比/趋势/占比关系时才加（type 可选 bar/line/pie），
values 只能是数字，数字必须来自用户材料，材料没有就不出图，不得为了配图编数据。"""


def generate_document(
    prompt: str, config: dict, preset_text: str = "", sub_skill: str | None = None
) -> dict:
    """一句话需求 -> 结构化办公文档 -> Word 文件。

    子能力（周报/纪要/策划/公告/简历）以 preset_text 注入结构约束，
    共用同一 JSON schema 与导出器；公告（notice）走公文红头排版。
    """
    system = DOC_SYSTEM_PROMPT
    if preset_text:
        system += f"\n\n【本文档类型约束】{preset_text}\n用户明确指定的要求优先于上述约束。"
    llm = get_llm_by_type(AGENT_LLM_MAP.get("reporter", "basic"))
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=prompt),
    ]
    resp = llm.invoke(messages, config=config)
    data = parse_json_response(resp.content)
    variant = "notice" if sub_skill == "notice" else "default"
    path = build_sections_docx(
        data, default_title="文档", prefix="document", variant=variant
    )
    return {"generated_file_path": path, "title": data.get("title", "文档")}
