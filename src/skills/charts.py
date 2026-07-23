# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""matplotlib(Agg) 数据图表 -> PNG bytes，供 Word 文档嵌入。

服务器无显示环境，强制 Agg 后端；中文标签依赖系统 CJK 字体，
探测不到时返回 None，调用方降级为文字列举（绝不输出豆腐块图）。
"""

import logging
from functools import lru_cache
from io import BytesIO

logger = logging.getLogger(__name__)

# 常见 CJK 字体，覆盖 macOS / Ubuntu(Noto/文泉驿) / Windows
_CJK_CANDIDATES = [
    "PingFang SC",
    "Hiragino Sans GB",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
    "WenQuanYi Zen Hei",
    "Microsoft YaHei",
    "SimHei",
    "Arial Unicode MS",
]

_PALETTE = ["#2E86C1", "#5DADE2", "#F5A623", "#76B041", "#8E6BB5", "#556070"]


@lru_cache(maxsize=1)
def _cjk_font() -> str | None:
    from matplotlib import font_manager

    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in _CJK_CANDIDATES:
        if name in installed:
            return name
    return None


def render_chart_png(chart: dict) -> bytes | None:
    """{type: bar|line|pie, title?, categories: [...], series: [{name, values}]}
    -> PNG bytes；数据不合法或无 CJK 字体时返回 None。"""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        font = _cjk_font()
        if font is None:
            logger.warning("no CJK font found, skip chart rendering")
            return None

        ctype = str(chart.get("type", "bar")).lower()
        categories = [str(c) for c in chart.get("categories", [])]
        series = chart.get("series", [])
        if not categories or not series:
            return None
        parsed = []
        for ser in series:
            values = [float(v) for v in ser.get("values", [])]
            if len(values) != len(categories):
                return None
            parsed.append((str(ser.get("name", "")), values))

        plt.rcParams["font.sans-serif"] = [font]
        plt.rcParams["axes.unicode_minus"] = False
        fig, ax = plt.subplots(figsize=(6.6, 3.4), dpi=160)
        if ctype == "pie":
            name, values = parsed[0]
            ax.pie(
                values,
                labels=categories,
                autopct="%1.1f%%",
                colors=_PALETTE[: len(values)],
                textprops={"fontsize": 9},
            )
        elif ctype == "line":
            for i, (name, values) in enumerate(parsed):
                ax.plot(categories, values, marker="o", linewidth=2,
                        color=_PALETTE[i % len(_PALETTE)], label=name or None)
        else:  # bar
            n = len(parsed)
            width = 0.8 / n
            for i, (name, values) in enumerate(parsed):
                offsets = [x + (i - (n - 1) / 2) * width for x in range(len(values))]
                ax.bar(offsets, values, width=width,
                       color=_PALETTE[i % len(_PALETTE)], label=name or None)
            ax.set_xticks(range(len(categories)))
            ax.set_xticklabels(categories, fontsize=9)
        if ctype != "pie":
            ax.tick_params(labelsize=9)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(axis="y", linewidth=0.4, alpha=0.4)
            if any(name for name, _ in parsed):
                ax.legend(fontsize=9, frameon=False)
        if chart.get("title"):
            ax.set_title(str(chart["title"]), fontsize=11)
        fig.tight_layout()
        buf = BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        logger.warning("chart rendering failed, fallback to text", exc_info=True)
        return None
