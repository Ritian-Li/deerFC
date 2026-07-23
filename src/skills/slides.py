# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""一句话需求 -> 结构化幻灯片 JSON -> pptx。

取代旧的 marp + chrome 管线：LLM 只产出版式化数据，渲染交给
pptx_export 的 python-pptx 版式库，图表为原生可编辑对象。
"""

from langchain.schema import HumanMessage, SystemMessage

from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.skills.common import parse_json_response
from src.skills.pptx_export import build_pptx

SLIDES_SYSTEM_PROMPT = """你是一位资深演示文稿设计顾问。根据用户需求产出一份结构化幻灯片数据，讲究「一页一个信息点、结论先行、数据说话」。

版式库（slides[].layout 可选值）：
- "agenda"：目录页。{"layout":"agenda","title":"目录","points":["…"]}
- "section"：章节分隔页。{"layout":"section","number":"01","title":"章节名","subtitle":"一句话导语"}
- "bullets"：要点页。{"layout":"bullets","title":"…","points":["…"],"insight":"本页一句话结论"}
- "kpi"：核心指标页，2~4 个大数字。{"layout":"kpi","title":"…","items":[{"value":"87%","label":"指标说明"}],"insight":"…"}
- "chart"：图表页。{"layout":"chart","chart_type":"bar|line|pie","title":"…","categories":["类目"],"series":[{"name":"系列名","values":[数字]}],"insight":"…"}
- "compare"：左右对比页。{"layout":"compare","title":"…","left":{"title":"…","points":["…"]},"right":{"title":"…","points":["…"]},"insight":"…"}
- "timeline"：流程/时间轴页，3~6 步。{"layout":"timeline","title":"…","steps":[{"label":"阶段","desc":"说明"}],"insight":"…"}
- "table"：表格页，≤9 行。{"layout":"table","title":"…","headers":["…"],"rows":[["…"]],"insight":"…"}
- "quote"：金句/观点页。{"layout":"quote","text":"…","source":"出处"}
- "end"：结尾页。{"layout":"end","title":"感谢聆听","subtitle":"…"}

硬性要求：
- 正文 8~14 页（封面自动生成，无需输出）；第一页用 agenda；超过 3 个部分时用 section 分隔；最后一页用 end。
- 版式要多样：连续的 bullets 不得超过 2 页；涉及数据时优先用 chart / kpi / table 呈现。
- 数据纪律：用户材料给出的数字必须原样使用；材料没有的数字可给合理估算，但须在该页 insight 中注明「估算」；严禁虚构精确到个位的假数据。用户未提及年份/日期时不要编造（写「上半年」就行，不要自己加年份）。chart 的 values 只能是数字（不带单位），单位写进 title 或 series name。
- 文字纪律：每页 points 不超过 6 条、每条不超过 30 字；insight 是一句给结论的话，不是复述标题。不使用 emoji。

只输出一个 JSON 对象，不要有任何多余文字或 markdown 围栏，格式：
{
  "title": "PPT 主标题",
  "subtitle": "副标题，可留空",
  "meta": "汇报人/日期行，用户没给就留空",
  "slides": [ … 按上面的版式库 … ]
}"""


def generate_slides(
    prompt: str, config: dict, preset_text: str = "", theme: str = "business"
) -> dict:
    """一句话需求 -> pptx。子能力预设注入制作要求，theme 决定配色版式风格。"""
    system = SLIDES_SYSTEM_PROMPT
    if preset_text:
        system += f"\n\n【本 PPT 类型约束】{preset_text}\n用户明确指定的要求优先于上述约束。"
    llm = get_llm_by_type(AGENT_LLM_MAP.get("ppt_composer", "basic"))
    resp = llm.invoke(
        [SystemMessage(content=system), HumanMessage(content=prompt)],
        config=config,
    )
    data = parse_json_response(resp.content)
    path = build_pptx(data, theme_name=theme)
    return {"generated_file_path": path, "title": data.get("title", "演示文稿")}
