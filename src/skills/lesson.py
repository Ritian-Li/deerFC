# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langchain.schema import HumanMessage, SystemMessage

from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.skills.common import parse_json_response
from src.skills.docx_export import (
    build_hwdesign_docx,
    build_lesson_docx,
    build_speech_docx,
)

LESSON_SYSTEM_PROMPT = """你是一位教学经验丰富的一线老师。根据用户要求撰写一份规范、可直接使用的教案。

要求：
- 准确理解用户指定的课题、学科、年级/学段、课时；用户没说的部分用最常见的合理默认值补全。
- 教学目标建议按「知识与技能、过程与方法、情感态度与价值观」三维或核心素养维度撰写。
- 教学过程要分环节（如：导入、新课讲授、巩固练习、课堂小结、布置作业），每个环节写清教师活动与学生活动。
- 内容符合对应学段课程标准，语言规范、可操作。

只输出一个 JSON 对象，不要有任何多余文字或 markdown 围栏，格式如下：
{
  "title": "课题名称，如：《春》教学设计",
  "meta": "学科 / 年级 / 课时，可留空",
  "objectives": ["教学目标1", "教学目标2"],
  "key_points": "教学重点",
  "difficulties": "教学难点",
  "process": [
    {"stage": "一、导入新课", "content": "教师活动与学生活动的详细描述"},
    {"stage": "二、新课讲授", "content": "..."},
    {"stage": "三、巩固练习", "content": "..."},
    {"stage": "四、课堂小结", "content": "..."}
  ],
  "blackboard": "板书设计",
  "homework": "作业布置",
  "reflection": "教学反思（可留空）"
}"""


SPEECH_SYSTEM_PROMPT = """你是一位参加说课比赛经验丰富的老师。根据用户要求撰写一份规范的说课稿。

要求：
- 准确理解用户指定的课题、学科、年级/学段；用户没说的部分用最常见的合理默认值补全。
- 按说课的标准框架撰写：说教材、说学情、说教学目标、说重难点、说教法学法、说教学过程、说板书设计、说教学反思。
- 「说教学过程」是重点，要说清每个环节做什么、为什么这样设计。
- 语言为第一人称口语化书面语（「我将采用…」「本环节的设计意图是…」）。

只输出一个 JSON 对象，不要有任何多余文字或 markdown 围栏，格式如下：
{
  "title": "《春》说课稿",
  "meta": "学科 / 年级，可留空",
  "sections": [
    {"heading": "一、说教材", "content": "…"},
    {"heading": "二、说学情", "content": "…"},
    {"heading": "三、说教学目标", "content": "…"},
    {"heading": "四、说重难点", "content": "…"},
    {"heading": "五、说教法学法", "content": "…"},
    {"heading": "六、说教学过程", "content": "…"},
    {"heading": "七、说板书设计", "content": "…"},
    {"heading": "八、说教学反思", "content": "…"}
  ]
}"""

HWDESIGN_SYSTEM_PROMPT = """你是一位深谙「双减」政策的教研员。根据用户要求设计一份分层作业。

要求：
- 准确理解用户指定的学科、年级/学段、知识点；用户没说的部分用最常见的合理默认值补全。
- 作业分三层：基础巩固（全员必做）、能力提升（多数学生）、拓展探究（学有余力）。
- 每层给出具体题目/任务（不是笼统描述），并写明该层设计意图与预计用时。
- 总量符合「双减」要求（小学书面作业不超过 60 分钟，初中不超过 90 分钟）。
- 数学公式用纯文本表达（如 x^2、√、≤），不要用 LaTeX。

只输出一个 JSON 对象，不要有任何多余文字或 markdown 围栏，格式如下：
{
  "title": "《一元二次方程》分层作业设计",
  "meta": "学科 / 年级 / 对应课时，可留空",
  "layers": [
    {
      "name": "A 层·基础巩固（必做）",
      "intent": "本层设计意图",
      "time": "预计用时，如：15 分钟",
      "items": ["1. 具体题目…", "2. 具体题目…"]
    },
    {"name": "B 层·能力提升", "intent": "…", "time": "…", "items": ["…"]},
    {"name": "C 层·拓展探究（选做）", "intent": "…", "time": "…", "items": ["…"]}
  ],
  "answers": "各层题目的参考答案（可合并写）",
  "note": "使用建议（可留空）"
}"""

# 子能力 -> (系统提示词, docx 构建函数, 默认标题)
_VARIANTS = {
    "speech": (SPEECH_SYSTEM_PROMPT, build_speech_docx, "说课稿"),
    "hwdesign": (HWDESIGN_SYSTEM_PROMPT, build_hwdesign_docx, "作业设计"),
}


def generate_lesson(
    prompt: str, config: dict, sub_skill: str | None = None, preset_text: str = ""
) -> dict:
    """一句话需求 -> 结构化教案/说课稿/分层作业 -> Word 文件。

    sub_skill 为 speech/hwdesign 时走独立提示词与导出格式；
    其余子能力（复习课/公开课）以 preset_text 追加约束，复用教案格式。
    """
    system, builder, default_title = _VARIANTS.get(
        sub_skill, (LESSON_SYSTEM_PROMPT, build_lesson_docx, "教案")
    )
    if preset_text and builder is build_lesson_docx:
        system += (
            f"\n\n【本教案类型约束】{preset_text}\n用户明确指定的要求优先于上述约束。"
        )
    llm = get_llm_by_type(AGENT_LLM_MAP.get("reporter", "basic"))
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=prompt),
    ]
    resp = llm.invoke(messages, config=config)
    data = parse_json_response(resp.content)
    path = builder(data)
    return {"generated_file_path": path, "title": data.get("title", default_title)}
