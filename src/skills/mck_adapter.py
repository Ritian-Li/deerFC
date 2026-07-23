# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""mck_ppt 引擎适配层：LLM 纯 JSON storyline -> DeckBuilder 调用。

LLM 永远不接触颜色/元组/Inches——这里统一注入配色轮换、转换数据形状、
执行上游 experiences 文档沉淀的防坑规则（标题长度、步骤数、标签单行等）。
坏页由 DeckBuilder 逐页跳过；跳过过半则整体报错（走"失败不扣次"）。
"""

import logging
import os
import uuid

from src.skills.mck_ppt.constants import (
    ACCENT_BLUE,
    ACCENT_PAIRS,
    LIGHT_BLUE,
    LIGHT_GREEN,
    LIGHT_ORANGE,
    LIGHT_RED,
    NAVY,
)

logger = logging.getLogger(__name__)

_LIGHTS = [LIGHT_BLUE, LIGHT_GREEN, LIGHT_ORANGE, LIGHT_RED]


def _s(v, limit: int = 0) -> str:
    text = str(v if v is not None else "").replace("\n", " ").strip()
    return text[:limit] if limit else text


def _title(d: dict) -> str:
    # 上游经验：action title 超 40 字符会溢出标题栏
    return _s(d.get("title", ""), 40)


def _tuples(items, *keys, limit=None, chars=()):
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        row = []
        for i, k in enumerate(keys):
            cap = chars[i] if i < len(chars) else 0
            row.append(_s(it.get(k, ""), cap))
        out.append(tuple(row))
    return out[:limit] if limit else out


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ---------- 各版式：LLM JSON -> engine kwargs ----------


def _cover(d):
    return {
        "title": _s(d.get("title", "演示文稿"), 60),
        "subtitle": _s(d.get("subtitle", "")),
        "author": _s(d.get("author", "")),
        "date": _s(d.get("date", "")),
    }


def _toc(d):
    items = _tuples(d.get("items"), "num", "title", "desc", limit=6, chars=(4, 20, 40))
    for i, row in enumerate(items):
        if not row[0]:
            items[i] = (f"{i + 1:02d}", row[1], row[2])
    return {"items": items}


def _section(d):
    return {
        "section_label": _s(d.get("label", "01"), 4),
        "title": _s(d.get("title", ""), 30),
        "subtitle": _s(d.get("subtitle", ""), 60),
    }


def _closing(d):
    return {"title": _s(d.get("title") or "感谢聆听", 30),
            "message": _s(d.get("message", ""), 80)}


def _big_number(d):
    return {
        "title": _title(d),
        "number": _s(d.get("number", ""), 16),
        "unit": _s(d.get("unit", ""), 8),
        "description": _s(d.get("description", ""), 60),
        "detail_items": [_s(x, 60) for x in d.get("details", [])][:4] or None,
    }


def _stats(d, n):
    stats = _tuples(d.get("stats"), "number", "label", limit=n, chars=(12, 30))
    stats = [(num, label, i % 2 == 0) for i, (num, label) in enumerate(stats)]
    return {
        "title": _title(d),
        "stats": stats,
        "detail_items": [_s(x, 70) for x in d.get("details", [])][:4] or None,
    }


def _metric_cards(d):
    return {"title": _title(d),
            "cards": _tuples(d.get("cards"), "tag", "title", "desc",
                             limit=4, chars=(3, 14, 90))}


def _data_table(d):
    headers = [_s(h, 14) for h in d.get("headers", [])][:6]
    rows = [[_s(c, 24) for c in row][: len(headers)]
            for row in d.get("rows", [])][:8]
    return {"title": _title(d), "headers": headers, "rows": rows}


def _table_insight(d):
    base = _data_table(d)
    # 右侧启示栏窄，行数更收敛
    base["headers"] = base["headers"][:4]
    base["rows"] = [r[:4] for r in base["rows"][:6]]
    base["insights"] = [_s(x, 60) for x in d.get("insights", [])][:4]
    return base


def _matrix_2x2(d):
    quads = _tuples(d.get("quadrants"), "label", "desc", limit=4, chars=(12, 80))
    quads = [(label, _LIGHTS[i % 4], desc) for i, (label, desc) in enumerate(quads)]
    axis = d.get("axis") or {}
    axis_labels = (
        (_s(axis.get("x", ""), 16), _s(axis.get("y", ""), 16))
        if axis.get("x") or axis.get("y") else None
    )
    return {"title": _title(d), "quadrants": quads, "axis_labels": axis_labels}


def _swot(d):
    quads = []
    for i, q in enumerate((d.get("quadrants") or [])[:4]):
        accent, light = ACCENT_PAIRS[i % 4]
        quads.append((_s(q.get("label", ""), 12), accent, light,
                      [_s(p, 40) for p in q.get("points", [])][:4]))
    return {"title": _title(d), "quadrants": quads}


def _chevron(d):
    # 上游经验：>5 步会挤爆；label 必须单行短标签
    steps = _tuples(d.get("steps"), "label", "title", "desc",
                    limit=5, chars=(8, 14, 50))
    return {"title": _title(d), "steps": steps}


def _timeline(d):
    ms = _tuples(d.get("milestones"), "label", "desc", limit=5, chars=(10, 40))
    if ms:  # 上游经验：最后一个标签超 6 字符必溢出右边界
        last = ms[-1]
        ms[-1] = (last[0][:6], last[1])
    return {"title": _title(d), "milestones": ms}


def _vertical_steps(d):
    steps = _tuples(d.get("steps"), "num", "title", "desc",
                    limit=5, chars=(4, 16, 70))
    for i, row in enumerate(steps):
        if not row[0]:
            steps[i] = (str(i + 1), row[1], row[2])
    return {"title": _title(d), "steps": steps}


def _four_column(d):
    items = _tuples(d.get("items"), "num", "title", "desc",
                    limit=4, chars=(4, 12, 120))
    for i, row in enumerate(items):
        if not row[0]:
            items[i] = (str(i + 1), row[1], row[2])
    return {"title": _title(d), "items": items}


def _pros_cons(d):
    conclusion = d.get("conclusion") or {}
    return {
        "title": _title(d),
        "pros_title": _s(d.get("pros_title") or "优势", 12),
        "pros": [_s(x, 50) for x in d.get("pros", [])][:5],
        "cons_title": _s(d.get("cons_title") or "劣势", 12),
        "cons": [_s(x, 50) for x in d.get("cons", [])][:5],
        "conclusion": ((_s(conclusion.get("label", "结论"), 8),
                        _s(conclusion.get("text", ""), 80))
                       if conclusion.get("text") else None),
    }


def _quote(d):
    return {"quote_text": _s(d.get("text", ""), 80),
            "attribution": _s(d.get("source", ""), 30)}


def _exec_summary(d):
    return {
        "title": _title(d),
        "headline": _s(d.get("headline", ""), 60),
        "items": _tuples(d.get("items"), "num", "title", "desc",
                         limit=4, chars=(4, 16, 90)),
    }


def _donut(d):
    segs = []
    for i, seg in enumerate((d.get("segments") or [])[:5]):
        segs.append((_num(seg.get("pct")), ACCENT_PAIRS[i % 4][0],
                     _s(seg.get("label", ""), 14)))
    return {
        "title": _title(d),
        "segments": segs,
        "center_label": _s(d.get("center_label", ""), 10),
        "center_sub": _s(d.get("center_sub", ""), 10),
    }


def _horizontal_bar(d):
    items = (d.get("items") or [])[:6]
    pcts = [_num(it.get("pct")) for it in items]
    top = pcts.index(max(pcts)) if pcts else -1
    rows = []
    for i, it in enumerate(items):
        color = NAVY if i == top else ACCENT_BLUE
        rows.append((_s(it.get("name", ""), 16), int(_num(it.get("pct"))), color))
    summary = d.get("summary") or {}
    return {
        "title": _title(d),
        "items": rows,
        "summary": ((_s(summary.get("label", "结论"), 8), _s(summary.get("text", ""), 80))
                    if summary.get("text") else None),
    }


def _grouped_bar(d):
    categories = [_s(c, 10) for c in d.get("categories", [])][:6]
    series_in = (d.get("series") or [])[:3]
    series = [(_s(s.get("name", ""), 12), ACCENT_PAIRS[i % 4][0])
              for i, s in enumerate(series_in)]
    data = []
    for ci in range(len(categories)):
        row = []
        for s in series_in:
            vals = s.get("values", [])
            row.append(_num(vals[ci]) if ci < len(vals) else 0)
        data.append(row)
    return {"title": _title(d), "categories": categories,
            "series": series, "data": data}


def _line_chart(d):
    values = [_num(v) for v in d.get("values", [])][:12]
    x_labels = [_s(x, 8) for x in d.get("x_labels", [])][: len(values)]
    peak = max(values) if values else 1.0
    peak = peak if peak > 0 else 1.0
    norm = [min(v / peak, 1.0) for v in values]
    unit = _s(d.get("unit", ""), 8)

    def fmt(v):
        text = f"{v:g}"
        return f"{text}{unit}" if unit else text

    return {
        "title": _title(d),
        "x_labels": x_labels,
        "y_labels": [fmt(0), fmt(peak / 2), fmt(peak)],
        "values": norm,
        "legend_label": _s(d.get("name", ""), 16),
    }


def _kpi_tracker(d):
    kpis = []
    for it in (d.get("kpis") or [])[:5]:
        status = str(it.get("status", "on")).lower()
        status = status if status in ("on", "risk", "off") else "on"
        kpis.append((_s(it.get("name", ""), 16), _num(it.get("pct")),
                     _s(it.get("detail", ""), 40), status))
    return {"title": _title(d), "kpis": kpis}


def _side_by_side(d):
    options = _tuples(d.get("options"), "title", limit=2, chars=(16,))
    opts = []
    for i, (opt_title,) in enumerate(options):
        points = (d.get("options") or [])[i].get("points", [])
        opts.append((opt_title, [_s(p, 50) for p in points][:5]))
    return {"title": _title(d), "options": opts}


_ADAPTERS = {
    "cover": _cover,
    "toc": _toc,
    "section_divider": _section,
    "closing": _closing,
    "big_number": _big_number,
    "two_stat": lambda d: _stats(d, 2),
    "three_stat": lambda d: _stats(d, 3),
    "metric_cards": _metric_cards,
    "data_table": _data_table,
    "table_insight": _table_insight,
    "matrix_2x2": _matrix_2x2,
    "swot": _swot,
    "process_chevron": _chevron,
    "timeline": _timeline,
    "vertical_steps": _vertical_steps,
    "four_column": _four_column,
    "pros_cons": _pros_cons,
    "quote": _quote,
    "executive_summary": _exec_summary,
    "donut": _donut,
    "horizontal_bar": _horizontal_bar,
    "grouped_bar": _grouped_bar,
    "line_chart": _line_chart,
    "kpi_tracker": _kpi_tracker,
    "side_by_side": _side_by_side,
}


def build_mck_deck(data: dict) -> str:
    """LLM storyline JSON -> 咨询风 pptx 文件路径。

    data: {"slides": [{"layout": "...", ...字段见 _ADAPTERS...}]}
    """
    from src.skills.mck_ppt.core import full_cleanup
    from src.skills.mck_ppt.engine import MckEngine

    raw_slides = [s for s in data.get("slides", []) if isinstance(s, dict)]
    storyline = []
    for s in raw_slides:
        layout = str(s.get("layout", "")).lower()
        adapter = _ADAPTERS.get(layout)
        if adapter is None:
            logger.warning("unknown mck layout %r, skipped", layout)
            continue
        try:
            storyline.append({"type": layout, "data": adapter(s)})
        except Exception:
            logger.warning("adapter failed for layout %r", layout, exc_info=True)
    if not storyline:
        raise ValueError("PPT 结构数据为空")
    if storyline[0]["type"] != "cover":
        storyline.insert(0, {"type": "cover", "data": _cover(data)})
    if storyline[-1]["type"] != "closing":
        storyline.append({"type": "closing", "data": _closing({})})

    eng = MckEngine(total_slides=len(storyline))
    errors = 0
    for spec in storyline:
        try:
            getattr(eng, spec["type"])(**spec["data"])
        except Exception:
            errors += 1
            logger.warning("mck layout %r render failed", spec["type"], exc_info=True)
    # 坏页跳过是常态容错；错过半说明 LLM 输出结构性崩坏，整体报错走"失败不扣次"
    if errors * 2 >= len(storyline):
        raise ValueError(f"PPT 渲染失败页过多（{errors}/{len(storyline)}）")
    path = os.path.join(os.getcwd(), f"slides_{uuid.uuid4().hex}.pptx")
    eng.save(path)
    full_cleanup(path)
    return path
