# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""PPT 主题常量库：颜色/字体全部代码化，不依赖模板文件。

借鉴社区 python-pptx 直出方案（Mck-ppt-design-skill 等）的思路：
样式即代码，一个主题一组常量，版式函数只读常量不写死颜色。
运营期调风格只改本文件。
"""

from dataclasses import dataclass, field

from pptx.dml.color import RGBColor


@dataclass(frozen=True)
class Theme:
    name: str
    # 主色：封面底、章节页底、标题文字
    primary: RGBColor
    # 强调色：标题下划线条、图表第一序列、时间轴节点
    accent: RGBColor
    # 图表/对比页的辅助序列色（含 accent 共 4 个）
    palette: tuple[RGBColor, ...]
    # 卡片/色带的浅底
    band: RGBColor
    text: RGBColor
    muted: RGBColor
    font_head: str = "微软雅黑"
    font_body: str = "微软雅黑"
    # 封面/章节页文字用色（深底白字）
    on_primary: RGBColor = field(default_factory=lambda: RGBColor(0xFF, 0xFF, 0xFF))


THEMES: dict[str, Theme] = {
    # 商务蓝：汇报、通用
    "business": Theme(
        name="business",
        primary=RGBColor(0x1F, 0x3A, 0x5F),
        accent=RGBColor(0x2E, 0x86, 0xC1),
        palette=(
            RGBColor(0x2E, 0x86, 0xC1),
            RGBColor(0x5D, 0xAD, 0xE2),
            RGBColor(0xF5, 0xA6, 0x23),
            RGBColor(0x76, 0xB0, 0x41),
        ),
        band=RGBColor(0xEE, 0xF4, 0xFA),
        text=RGBColor(0x21, 0x2A, 0x33),
        muted=RGBColor(0x6B, 0x77, 0x85),
    ),
    # 咨询灰黑：极简高对比，产品/项目路演
    "consult": Theme(
        name="consult",
        primary=RGBColor(0x17, 0x17, 0x17),
        accent=RGBColor(0x00, 0x85, 0xCA),
        palette=(
            RGBColor(0x00, 0x85, 0xCA),
            RGBColor(0x55, 0x5F, 0x6B),
            RGBColor(0xA6, 0xB2, 0xBF),
            RGBColor(0xE8, 0x9C, 0x1E),
        ),
        band=RGBColor(0xF2, 0xF2, 0xF0),
        text=RGBColor(0x1A, 0x1A, 0x1A),
        muted=RGBColor(0x73, 0x73, 0x73),
    ),
    # 学术墨绿：课件、培训、教学场景
    "academic": Theme(
        name="academic",
        primary=RGBColor(0x24, 0x50, 0x45),
        accent=RGBColor(0x3A, 0x8F, 0x6E),
        palette=(
            RGBColor(0x3A, 0x8F, 0x6E),
            RGBColor(0x7F, 0xB6, 0x9E),
            RGBColor(0xC9, 0x8B, 0x2D),
            RGBColor(0x5B, 0x77, 0x9A),
        ),
        band=RGBColor(0xEE, 0xF5, 0xF1),
        text=RGBColor(0x26, 0x2C, 0x28),
        muted=RGBColor(0x68, 0x74, 0x6D),
    ),
}

# 子能力 -> 主题（未知子能力回退 business）
SUB_SKILL_THEME: dict[str | None, str] = {
    None: "business",
    "general": "business",
    "workreport": "business",
    "pitch": "consult",
    "courseware": "academic",
    "training": "academic",
}


def resolve_theme(sub_skill: str | None) -> Theme:
    return THEMES[SUB_SKILL_THEME.get(sub_skill, "business")]
