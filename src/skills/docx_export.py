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


def build_sections_docx(
    data: dict, default_title: str = "文档", prefix: str = "doc"
) -> str:
    """通用「标题+小节」文档 -> docx。data: {title, meta?, sections:[{heading,content}]}。

    说课稿与办公文档（周报/纪要/策划/公告/简历）共用此结构。
    content 中的换行拆成独立段落，保持排版可读。
    """
    doc = _new_doc(data.get("title", default_title))
    meta = data.get("meta", "")
    if meta:
        p = doc.add_paragraph(meta)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for section in data.get("sections", []):
        doc.add_heading(section.get("heading", ""), level=1)
        for line in str(section.get("content", "")).split("\n"):
            if line.strip():
                doc.add_paragraph(line)
    return _save(doc, prefix)


def build_speech_docx(data: dict) -> str:
    """说课稿数据 -> docx。data: {title, meta?, sections:[{heading,content}]}."""
    return build_sections_docx(data, default_title="说课稿", prefix="speech")


def build_hwdesign_docx(data: dict) -> str:
    """分层作业数据 -> docx。data: {title, meta?, layers:[{name,intent?,time?,items:[]}],
    answers?, note?}."""
    doc = _new_doc(data.get("title", "分层作业设计"))
    meta = data.get("meta", "")
    if meta:
        p = doc.add_paragraph(meta)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for layer in data.get("layers", []):
        doc.add_heading(layer.get("name", ""), level=1)
        intent = layer.get("intent", "")
        time = layer.get("time", "")
        if intent or time:
            doc.add_paragraph(
                "　".join(
                    x
                    for x in (
                        f"设计意图：{intent}" if intent else "",
                        f"预计用时：{time}" if time else "",
                    )
                    if x
                )
            )
        for item in layer.get("items", []) or []:
            doc.add_paragraph(str(item))
    if data.get("answers"):
        doc.add_page_break()
        doc.add_heading("参考答案", level=1)
        doc.add_paragraph(str(data["answers"]))
    if data.get("note"):
        doc.add_heading("使用建议", level=1)
        doc.add_paragraph(str(data["note"]))
    return _save(doc, "hwdesign")
