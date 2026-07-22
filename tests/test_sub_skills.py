# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""子能力（sub_skill）预设与教育类导出的单元测试."""

import json
import os

from src.skills.presets import (
    SUB_SKILL_PRESETS,
    resolve_sub_skill,
    skill_label,
)


class TestResolveSubSkill:
    def test_missing_falls_back_to_v1(self):
        assert resolve_sub_skill("exam", None) == (None, "")
        assert resolve_sub_skill("exam", "") == (None, "")

    def test_unknown_id_falls_back_to_v1(self):
        assert resolve_sub_skill("exam", "nonexistent") == (None, "")
        assert resolve_sub_skill("nonexistent-skill", "quiz") == (None, "")

    def test_known_id_returns_preset(self):
        sub, text = resolve_sub_skill("exam", "quiz")
        assert sub == "quiz"
        assert "随堂测验" in text

    def test_default_subs_are_empty_presets(self):
        # research/ppt/lesson 的默认子能力 = v1 行为（无预设文本）
        for skill, default in (
            ("research", "general"),
            ("ppt", "general"),
            ("lesson", "newlesson"),
        ):
            _, text = resolve_sub_skill(skill, default)
            assert text == ""

    def test_labels_fit_db_column(self):
        # runs.skill 是 String(32)，复合串不能超长
        for skill, subs in SUB_SKILL_PRESETS.items():
            for sub in subs:
                assert len(skill_label(skill, sub)) <= 32

    def test_label_format(self):
        assert skill_label("exam", "quiz") == "exam:quiz"
        assert skill_label("exam", None) == "exam"


class TestDocxBuilders:
    def _check_and_remove(self, path):
        assert os.path.exists(path)
        assert os.path.getsize(path) > 10_000  # 是个真实的 docx
        os.remove(path)

    def test_build_speech_docx(self):
        from src.skills.docx_export import build_speech_docx

        path = build_speech_docx(
            {
                "title": "《春》说课稿",
                "meta": "语文 / 初一",
                "sections": [
                    {"heading": "一、说教材", "content": "本课选自…"},
                    {"heading": "二、说学情", "content": "初一学生…"},
                ],
            }
        )
        self._check_and_remove(path)

    def test_build_hwdesign_docx(self):
        from src.skills.docx_export import build_hwdesign_docx

        path = build_hwdesign_docx(
            {
                "title": "分层作业设计",
                "layers": [
                    {
                        "name": "A 层·基础巩固",
                        "intent": "巩固基本运算",
                        "time": "15 分钟",
                        "items": ["1. 解方程 x^2-4=0", "2. 解方程 x^2-2x=0"],
                    }
                ],
                "answers": "1. x=±2；2. x=0 或 x=2",
                "note": "建议独立完成",
            }
        )
        self._check_and_remove(path)


class _FakeLLM:
    """返回固定 JSON 的假模型，用于验证 lesson 子能力分发."""

    def __init__(self, payload):
        self._payload = payload

    def invoke(self, messages, config=None):
        class R:
            pass

        r = R()
        r.content = json.dumps(self._payload, ensure_ascii=False)
        # 记录 system prompt 供断言
        r.system = messages[0].content
        self._last_system = messages[0].content
        return r


class TestLessonDispatch:
    def test_speech_variant_uses_speech_prompt_and_builder(self, monkeypatch):
        import src.skills.lesson as lesson_mod

        fake = _FakeLLM(
            {
                "title": "《春》说课稿",
                "sections": [{"heading": "一、说教材", "content": "x"}],
            }
        )
        monkeypatch.setattr(lesson_mod, "get_llm_by_type", lambda _t: fake)
        result = lesson_mod.generate_lesson("《春》说课稿", {}, sub_skill="speech")
        assert "说课" in fake._last_system
        assert result["title"] == "《春》说课稿"
        os.remove(result["generated_file_path"])

    def test_preset_text_appended_for_regular_lesson(self, monkeypatch):
        import src.skills.lesson as lesson_mod

        fake = _FakeLLM({"title": "复习课教案", "objectives": ["o1"], "process": []})
        monkeypatch.setattr(lesson_mod, "get_llm_by_type", lambda _t: fake)
        result = lesson_mod.generate_lesson(
            "一元二次方程复习",
            {},
            sub_skill="review",
            preset_text="本教案为复习课教案。",
        )
        assert "复习课教案" in fake._last_system
        os.remove(result["generated_file_path"])

    def test_exam_preset_appended(self, monkeypatch):
        import src.skills.exam as exam_mod

        fake = _FakeLLM(
            {
                "title": "小测",
                "sections": [
                    {"type": "一、选择题", "questions": [{"stem": "q", "answer": "A"}]}
                ],
            }
        )
        monkeypatch.setattr(exam_mod, "get_llm_by_type", lambda _t: fake)
        result = exam_mod.generate_exam(
            "有理数 随堂测验", {}, preset_text="本卷用途：随堂测验。"
        )
        assert "随堂测验" in fake._last_system
        os.remove(result["generated_file_path"])
