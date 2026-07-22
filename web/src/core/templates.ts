// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * 启动台「模板灵感库」：办公场景为主的一键模板。
 * 每张卡 = 选中 (skill, subSkill) + 预填一段带【占位】的提示词——
 * 只封装真实可产出的能力（红线：宣传=真实调用），纯前端静态数据，
 * 运营期改文案不涉及部署风险。
 */

import type { SkillId } from "./skills";

export interface TemplateDef {
  id: string;
  name: string;
  emoji: string;
  /** 一句话场景说明（写给人看，≤18 字）。 */
  scene: string;
  skill: SkillId;
  subSkill: string;
  /** 点击后预填输入框的提示词，用【】占位待补信息。 */
  prompt: string;
}

export const TEMPLATES: TemplateDef[] = [
  {
    id: "weekly-report",
    name: "工作周报",
    emoji: "🗓️",
    scene: "五分钟交周报",
    skill: "doc",
    subSkill: "weekly",
    prompt:
      "帮我写本周工作周报：【部门/岗位】，本周完成了【事项1、事项2】，数据【关键数据】，下周计划【计划】",
  },
  {
    id: "meeting-minutes",
    name: "会议纪要",
    emoji: "🧾",
    scene: "散会即出纪要",
    skill: "doc",
    subSkill: "minutes",
    prompt:
      "整理会议纪要：【会议主题】，参会【人员】，讨论了【议题与结论】，定了【决议和分工】",
  },
  {
    id: "resume",
    name: "求职简历",
    emoji: "🧑‍💼",
    scene: "一页拿得出手",
    skill: "doc",
    subSkill: "resume",
    prompt:
      "帮我写一份求职简历：应聘【职位】，【学历/专业】，做过【工作或项目经历】，会【技能】",
  },
  {
    id: "notice",
    name: "通知公告",
    emoji: "📢",
    scene: "公文体不出错",
    skill: "doc",
    subSkill: "notice",
    prompt: "写一份通知：关于【事项】，时间【时间】，对象【全体员工/业主】，要求【要求】",
  },
  {
    id: "event-plan",
    name: "活动策划",
    emoji: "🎪",
    scene: "流程分工预算全",
    skill: "doc",
    subSkill: "plan",
    prompt: "做一份活动策划方案：【活动名称】，【人数】人，预算【金额】，时间【日期】",
  },
  {
    id: "timetable",
    name: "课程表",
    emoji: "🕐",
    scene: "排好节次时间",
    skill: "sheet",
    subSkill: "timetable",
    prompt: "排一张【年级】课程表：每天【节数】节，科目有【科目清单】，【特殊安排】",
  },
  {
    id: "duty-roster",
    name: "值日排班",
    emoji: "🧹",
    scene: "轮转均衡不扯皮",
    skill: "sheet",
    subSkill: "duty",
    prompt: "排一张值日/排班表：共【人数】人，每天【几人】，排【周期】，岗位有【岗位】",
  },
  {
    id: "budget",
    name: "预算明细",
    emoji: "💰",
    scene: "花销一目了然",
    skill: "sheet",
    subSkill: "budget",
    prompt: "做一份预算明细表：【用途】，总预算【金额】，包含【项目类别】",
  },
  {
    id: "work-ppt",
    name: "汇报 PPT",
    emoji: "💼",
    scene: "结构化亮成果",
    skill: "ppt",
    subSkill: "workreport",
    prompt: "做一份工作汇报 PPT：【部门/周期】，重点讲【目标完成情况、问题、计划】",
  },
  {
    id: "industry-report",
    name: "行业分析",
    emoji: "📈",
    scene: "带数据的深报告",
    skill: "research",
    subSkill: "finance",
    prompt: "深度分析【行业名称】：市场规模、竞争格局、机会与风险",
  },
  {
    id: "quiz",
    name: "随堂小卷",
    emoji: "⏱️",
    scene: "10 分钟当堂测",
    skill: "exam",
    subSkill: "quiz",
    prompt: "出一张随堂测验：【教材版本】【年级】【学科】，知识点【今天讲的内容】",
  },
  {
    id: "lesson-plan",
    name: "新课教案",
    emoji: "📚",
    scene: "环节齐全能直接用",
    skill: "lesson",
    subSkill: "newlesson",
    prompt: "写一份教案：【教材版本】【年级】【学科】《【课题】》，【课时数】课时",
  },
];
