# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""把结构化数据渲染成可打印的 Word 文档（试卷 / 教案）。纯 python-docx，无外部 CLI 依赖."""

import os
import uuid

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


def _new_doc(title: str) -> Document:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style.font.size = Pt(11)
    h = doc.add_heading(title, level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return doc


def _save(doc: Document, prefix: str) -> str:
    path = os.path.join(os.getcwd(), f"{prefix}_{uuid.uuid4().hex}.docx")
    doc.save(path)
    return path


def build_exam_docx(data: dict) -> str:
    """试卷数据 -> docx。data: {title, meta?, sections:[{type,instruction?,questions:[{stem,options?,answer,explanation?}]}]}."""
    doc = _new_doc(data.get("title", "试卷"))
    meta = data.get("meta", "")
    if meta:
        p = doc.add_paragraph(meta)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    q_index = 1
    answer_key = []  # (题号, 答案, 解析)
    for section in data.get("sections", []):
        heading = section.get("type", "题目")
        instr = section.get("instruction", "")
        doc.add_heading(f"{heading}{('　' + instr) if instr else ''}", level=1)
        for q in section.get("questions", []):
            stem = q.get("stem", "")
            doc.add_paragraph(f"{q_index}. {stem}")
            for opt in q.get("options", []) or []:
                doc.add_paragraph(str(opt), style="List Bullet")
            answer_key.append(
                (q_index, str(q.get("answer", "")), q.get("explanation", ""))
            )
            q_index += 1

    doc.add_page_break()
    doc.add_heading("参考答案与解析", level=1)
    for idx, ans, exp in answer_key:
        doc.add_paragraph(f"{idx}. 答案：{ans}")
        if exp:
            doc.add_paragraph(f"　　解析：{exp}")
    return _save(doc, "exam")


def build_lesson_docx(data: dict) -> str:
    """教案数据 -> docx。data: {title, meta?, objectives:[], key_points, difficulties,
    process:[{stage,content}], blackboard?, homework?, reflection?}."""
    doc = _new_doc(data.get("title", "教案"))
    meta = data.get("meta", "")
    if meta:
        p = doc.add_paragraph(meta)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    objectives = data.get("objectives", [])
    if objectives:
        doc.add_heading("一、教学目标", level=1)
        for o in objectives:
            doc.add_paragraph(str(o), style="List Number")

    if data.get("key_points"):
        doc.add_heading("二、教学重点", level=1)
        doc.add_paragraph(str(data["key_points"]))
    if data.get("difficulties"):
        doc.add_heading("三、教学难点", level=1)
        doc.add_paragraph(str(data["difficulties"]))

    process = data.get("process", [])
    if process:
        doc.add_heading("四、教学过程", level=1)
        for step in process:
            stage = step.get("stage", "")
            doc.add_heading(stage, level=2)
            doc.add_paragraph(str(step.get("content", "")))

    if data.get("blackboard"):
        doc.add_heading("五、板书设计", level=1)
        doc.add_paragraph(str(data["blackboard"]))
    if data.get("homework"):
        doc.add_heading("六、作业布置", level=1)
        doc.add_paragraph(str(data["homework"]))
    if data.get("reflection"):
        doc.add_heading("七、教学反思", level=1)
        doc.add_paragraph(str(data["reflection"]))
    return _save(doc, "lesson")
