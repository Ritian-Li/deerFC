// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Skill definitions for the chat "skill selector".
 * A skill turns the product from pure chat into a "one sentence, one
 * deliverable" tool. `research` uses the existing SSE flow; the other three
 * hit synchronous file-generating endpoints and return a downloadable blob.
 */

export type SkillId = "research" | "ppt" | "exam" | "lesson";

/** Skills that produce a downloadable file (non-SSE, synchronous). */
export type FileSkillId = "ppt" | "exam" | "lesson";

export interface SkillDef {
  id: SkillId;
  name: string;
  emoji: string;
  /** Placeholder shown in the input box when this skill is active. */
  placeholder: string;
  /** Example prompts. Clicking one selects the skill and fills the input. */
  examples: string[];
}

export const SKILLS: SkillDef[] = [
  {
    id: "research",
    name: "深度研究",
    emoji: "🔍",
    placeholder: "输入你想研究的问题…",
    examples: [
      "帮我调研 2025 年中国新能源汽车出口市场",
      "分析近三年短视频电商的发展趋势",
    ],
  },
  {
    id: "ppt",
    name: "做 PPT",
    emoji: "📊",
    placeholder: "描述你想要的 PPT 主题…",
    examples: [
      "帮我做一份「时间管理」主题的 PPT",
      "做一份关于人工智能发展史的 PPT",
    ],
  },
  {
    id: "exam",
    name: "智能组卷",
    emoji: "📝",
    placeholder: "学科/年级/知识点/题型/数量/难度…",
    examples: [
      "初中数学 一元二次方程 出10道选择题和5道解答题 中等难度",
      "高中英语 完形填空 出2篇 附答案",
    ],
  },
  {
    id: "lesson",
    name: "教案生成",
    emoji: "📚",
    placeholder: "课题/学科/年级/课时…",
    examples: [
      "人教版初一语文《春》 一课时 教案",
      "小学三年级数学《认识分数》 两课时 教案",
    ],
  },
];

export const DEFAULT_SKILL_ID: SkillId = "research";

const SKILL_MAP = new Map(SKILLS.map((s) => [s.id, s]));

export function getSkill(id: SkillId): SkillDef {
  return SKILL_MAP.get(id) ?? SKILLS[0]!;
}

export function isFileSkill(id: SkillId): id is FileSkillId {
  return id === "ppt" || id === "exam" || id === "lesson";
}

/** Config for each file-generating skill: endpoint, request body key, UI copy. */
export const FILE_SKILL_CONFIG: Record<
  FileSkillId,
  {
    /** API path relative to the /api/ base (see resolveServiceURL). */
    path: string;
    /** JSON body key that carries the user's text ("content" or "prompt"). */
    bodyKey: "content" | "prompt";
    /** Loading copy shown while generating. */
    loadingText: string;
    /** Default filename when Content-Disposition can't be parsed. */
    defaultFilename: string;
  }
> = {
  ppt: {
    path: "ppt/generate",
    bodyKey: "content",
    loadingText: "正在生成 PPT，请稍候（约需 30~60 秒）…",
    defaultFilename: "PPT.pptx",
  },
  exam: {
    path: "exam/generate",
    bodyKey: "prompt",
    loadingText: "正在生成试卷，请稍候（约需 30~60 秒）…",
    defaultFilename: "试卷.docx",
  },
  lesson: {
    path: "lesson/generate",
    bodyKey: "prompt",
    loadingText: "正在生成教案，请稍候（约需 30~60 秒）…",
    defaultFilename: "教案.docx",
  },
};
