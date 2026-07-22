# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langchain.schema import HumanMessage, SystemMessage

from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.skills.common import parse_json_response
from src.skills.docx_export import build_lesson_docx

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


def generate_lesson(prompt: str, config: dict) -> dict:
    """一句话需求 -> 结构化教案 -> Word 文件。config 携带 token 计量 callback."""
    llm = get_llm_by_type(AGENT_LLM_MAP.get("reporter", "basic"))
    messages = [
        SystemMessage(content=LESSON_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    resp = llm.invoke(messages, config=config)
    data = parse_json_response(resp.content)
    path = build_lesson_docx(data)
    return {"generated_file_path": path, "title": data.get("title", "教案")}
