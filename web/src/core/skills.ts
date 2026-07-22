// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Skill definitions for the chat "skill selector".
 * A skill turns the product from pure chat into a "one sentence, one
 * deliverable" tool. `research` uses the existing SSE flow; the other three
 * hit synchronous file-generating endpoints and return a downloadable blob.
 *
 * v2: each skill has 3~5 sub-skills (scenario presets). Picking one sends
 * `sub_skill` to the backend which injects a prompt preset — no new billing
 * dimension, no new endpoints. The first sub-skill of each skill is the
 * default and (except exam) matches v1 behavior.
 */

export type SkillId = "research" | "ppt" | "doc" | "sheet" | "exam" | "lesson";

/** Skills that produce a downloadable file (non-SSE, synchronous). */
export type FileSkillId = "ppt" | "doc" | "sheet" | "exam" | "lesson";

/** Card theme; maps to static tailwind classes in the selector component. */
export type SkillTheme = "blue" | "orange" | "cyan" | "teal" | "green" | "purple";

/** CSS 绘制的成品缩略预览类型（见 mini-preview.tsx）。 */
export type PreviewKind =
  | "report"
  | "chart"
  | "swot"
  | "cite"
  | "clauses"
  | "slide"
  | "slide-chart"
  | "slide-steps"
  | "slide-hero"
  | "checklist"
  | "minutes"
  | "timeline"
  | "notice"
  | "resume"
  | "grid"
  | "grid-status"
  | "grid-total"
  | "exam"
  | "lesson";

export interface SubSkillDef {
  id: string;
  name: string;
  emoji: string;
  /** One-line description shown under the card row when selected (≤20 chars). */
  desc: string;
  /** 成品缩略预览的画法。 */
  preview: PreviewKind;
  /** Placeholder for the input box while this sub-skill is active. */
  placeholder: string;
  /** Example prompts (include 教材版本+年级 for edu skills). */
  examples: string[];
}

export interface SkillDef {
  id: SkillId;
  name: string;
  emoji: string;
  theme: SkillTheme;
  subSkills: SubSkillDef[];
}

export const SKILLS: SkillDef[] = [
  {
    id: "research",
    name: "深度研究",
    emoji: "🔍",
    theme: "blue",
    subSkills: [
      {
        id: "general",
        name: "通用调研",
        emoji: "🔍",
        desc: "任何主题的深度研究报告",
        preview: "report",
        placeholder: "输入你想研究的问题…",
        examples: [
          "帮我调研 2025 年中国新能源汽车出口市场",
          "分析近三年短视频电商的发展趋势",
        ],
      },
      {
        id: "finance",
        name: "行业分析",
        emoji: "📈",
        desc: "行业规模·格局·风险机会",
        preview: "chart",
        placeholder: "输入行业或公司…",
        examples: [
          "分析国内储能行业的竞争格局和投资机会",
          "调研预制菜行业近两年的发展与头部玩家",
        ],
      },
      {
        id: "market",
        name: "市场调研",
        emoji: "🛒",
        desc: "市场规模·用户·竞品对比",
        preview: "swot",
        placeholder: "输入产品或市场…",
        examples: [
          "调研三线城市开一家宠物店的市场情况",
          "帮我做奶茶品牌加盟的市场调研",
        ],
      },
      {
        id: "academic",
        name: "文献综述",
        emoji: "🎓",
        desc: "研究脉络·观点对比·空白",
        preview: "cite",
        placeholder: "输入研究方向或论文主题…",
        examples: [
          "大语言模型在教育领域应用的研究综述",
          "近五年乡村振兴政策研究的文献综述",
        ],
      },
      {
        id: "policy",
        name: "政策解读",
        emoji: "📜",
        desc: "政策要点·影响·应对建议",
        preview: "clauses",
        placeholder: "输入政策名称或领域…",
        examples: [
          "解读最新的新能源汽车购置税优惠政策",
          "双减政策对课外培训行业的影响分析",
        ],
      },
    ],
  },
  {
    id: "ppt",
    name: "做 PPT",
    emoji: "📊",
    theme: "orange",
    subSkills: [
      {
        id: "general",
        name: "通用演示",
        emoji: "📊",
        desc: "任意主题的演示文稿",
        preview: "slide",
        placeholder: "描述你想要的 PPT 主题…",
        examples: [
          "帮我做一份「时间管理」主题的 PPT",
          "做一份关于人工智能发展史的 PPT",
        ],
      },
      {
        id: "workreport",
        name: "工作汇报",
        emoji: "💼",
        desc: "目标·成果·问题·计划",
        preview: "slide-chart",
        placeholder: "描述汇报内容（部门/周期/重点）…",
        examples: [
          "Q2 销售部季度复盘汇报 PPT",
          "做一份运营部月度工作总结 PPT",
        ],
      },
      {
        id: "courseware",
        name: "教学课件",
        emoji: "🧑‍🏫",
        desc: "目标·讲解·例题·练习",
        preview: "slide-steps",
        placeholder: "课题/学科/年级…",
        examples: [
          "人教版九上数学《一元二次方程》第一课时课件",
          "初一语文《春》教学课件",
        ],
      },
      {
        id: "pitch",
        name: "产品介绍",
        emoji: "🚀",
        desc: "痛点·方案·亮点·案例",
        preview: "slide-hero",
        placeholder: "描述产品/项目和亮点…",
        examples: [
          "智能手环新品发布介绍 PPT",
          "社区团购项目的招商介绍 PPT",
        ],
      },
      {
        id: "training",
        name: "培训分享",
        emoji: "📣",
        desc: "概念·方法·案例·练习",
        preview: "slide-steps",
        placeholder: "培训主题/对象…",
        examples: [
          "新员工时间管理培训 PPT",
          "客服沟通技巧内训 PPT",
        ],
      },
    ],
  },
  {
    id: "doc",
    name: "办公文档",
    emoji: "📄",
    theme: "cyan",
    subSkills: [
      {
        id: "weekly",
        name: "周报总结",
        emoji: "🗓️",
        desc: "完成事项·数据亮点·下周计划",
        preview: "checklist",
        placeholder: "本周做了什么（部门/事项/数据）…",
        examples: [
          "运营部本周周报：上新3个SKU，GMV环比+12%，下周筹备大促",
          "个人月度工作总结：负责的小程序上线，DAU破1万",
        ],
      },
      {
        id: "minutes",
        name: "会议纪要",
        emoji: "🧾",
        desc: "议题结论·决议·行动项",
        preview: "minutes",
        placeholder: "会议主题/讨论要点/结论…",
        examples: [
          "周一产品例会纪要：讨论了改版方案，定了7月底上线，张三负责开发排期",
          "家委会会议纪要：确定秋游时间和费用分摊",
        ],
      },
      {
        id: "plan",
        name: "活动策划",
        emoji: "🎪",
        desc: "目标·流程·分工·预算",
        preview: "timeline",
        placeholder: "活动类型/时间/对象/预算…",
        examples: [
          "公司10周年庆活动策划方案，200人，预算5万",
          "幼儿园六一亲子活动策划，室内外结合",
        ],
      },
      {
        id: "notice",
        name: "通知公告",
        emoji: "📢",
        desc: "规范公文体·语气得体",
        preview: "notice",
        placeholder: "通知什么事/给谁/有什么要求…",
        examples: [
          "写一份放假通知：国庆放假8天，值班安排另行通知",
          "物业停水通知：周六上午9点到下午5点检修",
        ],
      },
      {
        id: "resume",
        name: "个人简历",
        emoji: "🧑‍💼",
        desc: "STAR经历·量化成果",
        preview: "resume",
        placeholder: "职位方向/教育背景/工作经历…",
        examples: [
          "3年电商运营经验求职简历，做过直播带货，最高单场50万",
          "应届计算机本科生简历，两段实习经历",
        ],
      },
    ],
  },
  {
    id: "sheet",
    name: "数据表格",
    emoji: "📋",
    theme: "teal",
    subSkills: [
      {
        id: "general",
        name: "通用表格",
        emoji: "📋",
        desc: "任意需求整理成规范表格",
        preview: "grid",
        placeholder: "描述你要的表格（行/列/内容）…",
        examples: [
          "把班级50名学生按成绩分组，做一张分组名单表",
          "整理一份家庭月度开支记录表",
        ],
      },
      {
        id: "timetable",
        name: "课程表",
        emoji: "🕐",
        desc: "节次×星期·含时间段",
        preview: "grid",
        placeholder: "年级/每天几节/科目安排…",
        examples: [
          "初一课程表：每天8节，主科每天都有，周五下午社团",
          "小学三年级课程表，每天6节课",
        ],
      },
      {
        id: "duty",
        name: "值日排班",
        emoji: "🧹",
        desc: "轮转均衡·职责清晰",
        preview: "grid-status",
        placeholder: "人数/周期/岗位…",
        examples: [
          "班级45人每天6人值日，按周轮转排一个月",
          "店里5个店员排下个月的早晚班",
        ],
      },
      {
        id: "budget",
        name: "预算明细",
        emoji: "💰",
        desc: "单价·数量·小计·合计",
        preview: "grid-total",
        placeholder: "预算用途/项目/大致金额…",
        examples: [
          "班级元旦晚会预算表，总预算2000元",
          "小型奶茶店开店预算明细表",
        ],
      },
      {
        id: "tracker",
        name: "计划进度",
        emoji: "📅",
        desc: "任务·负责人·起止·状态",
        preview: "grid-status",
        placeholder: "项目内容/阶段/周期…",
        examples: [
          "装修工程3个月进度计划表，含水电木瓦油各阶段",
          "毕业论文写作3个月推进计划表",
        ],
      },
    ],
  },
  {
    id: "exam",
    name: "智能组卷",
    emoji: "📝",
    theme: "green",
    subSkills: [
      {
        id: "unit",
        name: "单元测试",
        emoji: "📝",
        desc: "45~60分钟·题型完整",
        preview: "exam",
        placeholder: "学科/年级/单元/题型/数量…",
        examples: [
          "人教版九上数学 一元二次方程单元测试 10道选择5道解答",
          "人教版八下物理 力与运动单元测试卷",
        ],
      },
      {
        id: "quiz",
        name: "随堂测验",
        emoji: "⏱️",
        desc: "10~15分钟小卷·当堂知识点",
        preview: "exam",
        placeholder: "学科/年级/今天讲的知识点…",
        examples: [
          "人教版七上数学 有理数加减法 随堂测验",
          "初二英语 一般过去时 10分钟小测",
        ],
      },
      {
        id: "homework",
        name: "家庭作业",
        emoji: "🏠",
        desc: "30~40分钟·解析详细可批改",
        preview: "exam",
        placeholder: "学科/年级/知识点/题量…",
        examples: [
          "人教版五年级数学 分数加减法 家庭作业15题",
          "初一语文 病句修改 家庭作业",
        ],
      },
      {
        id: "exam",
        name: "期中期末",
        emoji: "🎯",
        desc: "90分钟综合卷·含压轴题",
        preview: "exam",
        placeholder: "学科/年级/考试范围…",
        examples: [
          "人教版九上数学期中模拟卷（前三章）",
          "人教版八年级英语上册期末模拟卷",
        ],
      },
      {
        id: "topic",
        name: "专题训练",
        emoji: "🎪",
        desc: "单知识点·阶梯递进·易错提示",
        preview: "exam",
        placeholder: "学科/年级/要强化的知识点…",
        examples: [
          "初三数学 二次函数最值问题 专题训练20题",
          "高一物理 受力分析专题训练",
        ],
      },
    ],
  },
  {
    id: "lesson",
    name: "教案生成",
    emoji: "📚",
    theme: "purple",
    subSkills: [
      {
        id: "newlesson",
        name: "新授课",
        emoji: "📚",
        desc: "导入·新授·巩固·小结",
        preview: "lesson",
        placeholder: "课题/学科/年级/课时…",
        examples: [
          "人教版初一语文《春》 一课时 教案",
          "人教版三年级数学《认识分数》 教案",
        ],
      },
      {
        id: "review",
        name: "复习课",
        emoji: "🔁",
        desc: "知识梳理·例题·易错辨析",
        preview: "lesson",
        placeholder: "复习范围/学科/年级…",
        examples: [
          "人教版九上数学 一元二次方程复习课教案",
          "初二英语期中复习课教案（前四单元）",
        ],
      },
      {
        id: "openclass",
        name: "公开课",
        emoji: "🌟",
        desc: "含设计意图·精确到分钟",
        preview: "lesson",
        placeholder: "课题/学科/年级…",
        examples: [
          "人教版初一语文《春》公开课教案",
          "人教版四年级数学《平行四边形》优质课教案",
        ],
      },
      {
        id: "speech",
        name: "说课稿",
        emoji: "🎤",
        desc: "说教材·学情·教法·过程",
        preview: "cite",
        placeholder: "课题/学科/年级…",
        examples: [
          "人教版初一语文《春》说课稿",
          "人教版八上物理《压强》说课稿",
        ],
      },
      {
        id: "hwdesign",
        name: "作业设计",
        emoji: "✏️",
        desc: "双减分层作业·三层设计",
        preview: "checklist",
        placeholder: "学科/年级/知识点…",
        examples: [
          "人教版七上数学 整式的加减 分层作业设计",
          "人教版五年级语文《白鹭》分层作业",
        ],
      },
    ],
  },
];

export const DEFAULT_SKILL_ID: SkillId = "research";

const SKILL_MAP = new Map(SKILLS.map((s) => [s.id, s]));

export function getSkill(id: SkillId): SkillDef {
  return SKILL_MAP.get(id) ?? SKILLS[0]!;
}

/** Default sub-skill = the first one of the skill. */
export function getDefaultSubSkillId(skillId: SkillId): string {
  return getSkill(skillId).subSkills[0]!.id;
}

/** Resolve a sub-skill; unknown ids fall back to the skill's default. */
export function getSubSkill(skillId: SkillId, subId: string): SubSkillDef {
  const skill = getSkill(skillId);
  return skill.subSkills.find((s) => s.id === subId) ?? skill.subSkills[0]!;
}

export function isFileSkill(id: SkillId): id is FileSkillId {
  return id !== "research";
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
  doc: {
    path: "doc/generate",
    bodyKey: "prompt",
    loadingText: "正在生成文档，请稍候（约需 30~60 秒）…",
    defaultFilename: "文档.docx",
  },
  sheet: {
    path: "sheet/generate",
    bodyKey: "prompt",
    loadingText: "正在生成表格，请稍候（约需 30~60 秒）…",
    defaultFilename: "表格.xlsx",
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
    loadingText: "正在生成文档，请稍候（约需 30~60 秒）…",
    defaultFilename: "教案.docx",
  },
};
