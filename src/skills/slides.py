# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""一句话需求 -> 结构化幻灯片 JSON -> pptx。

默认引擎为 vendored 的 mck_ppt（McKinsey 咨询风设计系统，Apache-2.0，
见 src/skills/mck_ppt/NOTICE）：LLM 出 storyline JSON，mck_adapter 注入
配色/防坑规则后由引擎渲染。设 PLATFORM_PPT_ENGINE=classic 可回退到
本项目自研的 pptx_export 多主题管线（原生可编辑图表）。
"""

import os

from langchain.schema import HumanMessage, SystemMessage

from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.skills.common import parse_json_response
from src.skills.mck_adapter import build_mck_deck
from src.skills.pptx_export import build_pptx

MCK_SYSTEM_PROMPT = """你是麦肯锡出身的演示文稿设计顾问。根据用户需求产出一份咨询级幻灯片结构数据（storyline），讲究「行动标题、结论先行、一页一论点、数据说话」。

版式库（slides[].layout 及其字段）：
- "cover"：封面 {"layout":"cover","title":"…","subtitle":"…","author":"…","date":"…"}（author/date 用户没给就留空字符串）
- "toc"：目录 {"layout":"toc","items":[{"num":"01","title":"…","desc":"一句话说明"}]}，≤6 项
- "section_divider"：章节页 {"layout":"section_divider","label":"01","title":"…","subtitle":"…"}
- "executive_summary"：执行摘要 {"layout":"executive_summary","title":"…","headline":"一句核心结论","items":[{"num":"1","title":"…","desc":"…"}]}
- "big_number"：单个关键数字 {"layout":"big_number","title":"…","number":"1,200","unit":"人","description":"…","details":["…"]}
- "two_stat" / "three_stat"：2/3 个并列大数字 {"layout":"two_stat","title":"…","stats":[{"number":"45%","label":"…"}],"details":["…"]}
- "metric_cards"：3~4 张要点卡 {"layout":"metric_cards","title":"…","cards":[{"tag":"A","title":"…","desc":"…"}]}
- "data_table"：数据表 {"layout":"data_table","title":"…","headers":["…"],"rows":[["…"]]}，≤6 列 8 行
- "table_insight"：表格+右侧启示栏 {"layout":"table_insight","title":"…","headers":["…"],"rows":[["…"]],"insights":["…"]}，≤4 列 6 行
- "matrix_2x2"：2×2 矩阵 {"layout":"matrix_2x2","title":"…","quadrants":[{"label":"…","desc":"…"}×4],"axis":{"x":"…","y":"…"}}
- "swot"：SWOT {"layout":"swot","title":"…","quadrants":[{"label":"优势","points":["…"]}×4]}
- "process_chevron"：横向流程 {"layout":"process_chevron","title":"…","steps":[{"label":"01","title":"…","desc":"…"}]}，2~5 步，label 是不换行短标签
- "timeline"：时间轴 {"layout":"timeline","title":"…","milestones":[{"label":"Q3","desc":"…"}]}，≤5 个，最后一个 label ≤6 字
- "vertical_steps"：纵向步骤 {"layout":"vertical_steps","title":"…","steps":[{"num":"1","title":"…","desc":"…"}]}，≤5 步
- "four_column"：四栏概览 {"layout":"four_column","title":"…","items":[{"num":"1","title":"…","desc":"…"}]}，desc ≤120 字
- "pros_cons"：利弊分析 {"layout":"pros_cons","title":"…","pros_title":"…","pros":["…"],"cons_title":"…","cons":["…"],"conclusion":{"label":"结论","text":"…"}}
- "side_by_side"：两方案对比 {"layout":"side_by_side","title":"…","options":[{"title":"…","points":["…"]}×2]}
- "quote"：金句页 {"layout":"quote","text":"…","source":"…"}
- "donut"：占比环图 {"layout":"donut","title":"…","segments":[{"label":"…","pct":45}],"center_label":"45%","center_sub":"…"}，≤5 段、pct 合计≈100
- "horizontal_bar"：横向条形图 {"layout":"horizontal_bar","title":"…","items":[{"name":"…","pct":72}],"summary":{"label":"结论","text":"…"}}，pct 为 0~100
- "grouped_bar"：分组柱状图 {"layout":"grouped_bar","title":"…","categories":["Q1","Q2"],"series":[{"name":"…","values":[数字]}]}，≤6 类目 3 系列
- "line_chart"：折线图 {"layout":"line_chart","title":"…","x_labels":["1月"],"values":[原始数字],"unit":"万","name":"系列名"}
- "kpi_tracker"：KPI 进度 {"layout":"kpi_tracker","title":"…","kpis":[{"name":"…","pct":80,"detail":"…","status":"on|risk|off"}]}
- "closing"：结尾 {"layout":"closing","title":"感谢聆听","message":"…"}

硬性要求：
- 行动标题：除封面/章节页外，每页 title 必须是带结论的判断句（≤40 字），如「Q2 GMV 环比增长 31%，直播渠道贡献过半」；禁止「Q2 业绩」这类名词短语。
- 结构：cover → toc → executive_summary →（section_divider + 该章 2~4 页内容）× 2~4 章 → closing；总计 10~16 页。
- 版式多样：同一版式连续不超过 2 页；出现数据时优先用图表/数字类版式，不要塞进要点列表。
- 数据纪律：用户材料给出的数字原样使用；材料没有的可合理估算但须在该页 desc/summary 注明「估算」；严禁虚构精确假数据；用户未提及年份就不要编造年份。
- 文字纪律：全中文（专有名词除外）、不用 emoji；desc 类字段是短句不是段落。

只输出一个 JSON 对象，不要任何多余文字或 markdown 围栏：
{"slides":[{"layout":"cover",…},{"layout":"toc",…},…]}"""

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
    """一句话需求 -> pptx。子能力预设注入制作要求。

    默认 mck 引擎（咨询级设计系统）；PLATFORM_PPT_ENGINE=classic 回退
    自研多主题管线（theme 仅 classic 模式生效）。
    """
    engine = os.getenv("PLATFORM_PPT_ENGINE", "mck").lower()
    system = MCK_SYSTEM_PROMPT if engine == "mck" else SLIDES_SYSTEM_PROMPT
    if preset_text:
        system += f"\n\n【本 PPT 类型约束】{preset_text}\n用户明确指定的要求优先于上述约束。"
    llm = get_llm_by_type(AGENT_LLM_MAP.get("ppt_composer", "basic"))
    resp = llm.invoke(
        [SystemMessage(content=system), HumanMessage(content=prompt)],
        config=config,
    )
    data = parse_json_response(resp.content)
    if engine == "mck":
        path = build_mck_deck(data)
        slides = data.get("slides") or [{}]
        title = str(slides[0].get("title", "演示文稿"))
    else:
        path = build_pptx(data, theme_name=theme)
        title = data.get("title", "演示文稿")
    return {"generated_file_path": path, "title": title}
