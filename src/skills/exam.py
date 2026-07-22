# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langchain.schema import HumanMessage, SystemMessage

from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.skills.common import parse_json_response
from src.skills.docx_export import build_exam_docx

EXAM_SYSTEM_PROMPT = """你是一位经验丰富的命题老师。根据用户的要求出一份试卷。

要求：
- 准确理解用户指定的学科、年级/学段、知识点、题型、题量、难度；用户没说的部分用最常见的合理默认值补全。
- 题目要符合对应学段的课程标准，表述规范、无歧义，难度分布合理。
- 每道题都必须给出正确答案；除纯客观的判断题外，尽量给出简要解析。
- 数学公式用纯文本表达（如 x^2、√、≤），不要用 LaTeX。

只输出一个 JSON 对象，不要有任何多余文字或 markdown 围栏，格式如下：
{
  "title": "试卷标题，如：初中数学《一元二次方程》单元测试",
  "meta": "副标题信息，如：年级 / 满分 / 时长，可留空",
  "sections": [
    {
      "type": "一、选择题（每题3分）",
      "instruction": "本大题的作答说明，可留空",
      "questions": [
        {
          "stem": "题干",
          "options": ["A. 选项", "B. 选项", "C. 选项", "D. 选项"],
          "answer": "B",
          "explanation": "简要解析"
        }
      ]
    },
    {
      "type": "二、解答题（每题10分）",
      "questions": [
        {"stem": "题干", "answer": "参考答案", "explanation": "解题步骤"}
      ]
    }
  ]
}
非选择题的 options 省略即可。"""


def generate_exam(prompt: str, config: dict, preset_text: str = "") -> dict:
    """一句话需求 -> 结构化试卷 -> Word 文件。config 携带 token 计量 callback.

    preset_text: 子能力（随堂测验/家庭作业等）的用途约束，追加在 system prompt
    末尾兜底未指定项；用户输入的显式要求（如题量）优先于预设。
    """
    llm = get_llm_by_type(AGENT_LLM_MAP.get("reporter", "basic"))
    system = EXAM_SYSTEM_PROMPT
    if preset_text:
        system += (
            f"\n\n【本卷用途约束】{preset_text}\n用户明确指定的要求优先于上述约束。"
        )
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=prompt),
    ]
    resp = llm.invoke(messages, config=config)
    data = parse_json_response(resp.content)
    path = build_exam_docx(data)
    return {"generated_file_path": path, "title": data.get("title", "试卷")}
