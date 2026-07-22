// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { getSkill, getSubSkill } from "~/core/skills";
import { setCurrentSkill, setCurrentSubSkill } from "~/core/store";
import { TEMPLATES, type TemplateDef } from "~/core/templates";
import { cn } from "~/lib/utils";

import { MiniPreview } from "./mini-preview";

/**
 * 启动台模板灵感库（仅 hero/空会话展示）。
 * 每张卡上半部是 CSS 绘制的「成品缩略预览」（A4 文档/表格/幻灯片/试卷），
 * 点卡片 = 选中技能+子能力 + 预填提示词。横向滚动控制启动台总高度。
 */
export function TemplateGallery({
  className,
  onPickTemplate,
}: {
  className?: string;
  onPickTemplate: (prompt: string) => void;
}) {
  const handlePick = (template: TemplateDef) => {
    setCurrentSkill(template.skill);
    setCurrentSubSkill(template.subSkill);
    onPickTemplate(template.prompt);
  };
  return (
    <div className={cn("w-full", className)}>
      <div className="text-muted-foreground mb-2 px-1 text-xs font-medium">
        ✨ 常用模板 · 点一下，填空就能用
      </div>
      <div className="scrollbar-hide -mx-1 flex gap-2.5 overflow-x-auto px-1 pb-1">
        {TEMPLATES.map((template) => {
          const skill = getSkill(template.skill);
          const sub = getSubSkill(template.skill, template.subSkill);
          return (
            <button
              key={template.id}
              type="button"
              onClick={() => handlePick(template)}
              className="group bg-card hover:border-brand/50 flex w-[128px] shrink-0 cursor-pointer flex-col overflow-hidden rounded-xl border text-left transition-colors"
            >
              <div className="bg-accent/40 flex h-[88px] w-full items-center justify-center transition-colors group-hover:bg-accent/60">
                <MiniPreview kind={sub.preview} theme={skill.theme} className="h-[68px]" />
              </div>
              <div className="flex flex-col gap-0.5 px-2.5 py-2">
                <span className="text-xs font-medium">{template.name}</span>
                <span className="text-muted-foreground truncate text-[10px]">
                  {template.scene}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
