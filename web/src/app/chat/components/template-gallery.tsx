// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { getSkill, type SkillTheme } from "~/core/skills";
import { setCurrentSkill, setCurrentSubSkill } from "~/core/store";
import { TEMPLATES, type TemplateDef } from "~/core/templates";
import { cn } from "~/lib/utils";

/**
 * 启动台模板灵感库（仅 hero/空会话展示）。
 * 点卡片 = 选中技能+子能力 + 预填提示词，视觉沿用子能力卡的
 * 「技能主题色渐变底」语言，让模板一眼看出归属哪个能力。
 */

const CARD_THEME: Record<SkillTheme, string> = {
  blue: "from-blue-500/10 to-transparent hover:border-blue-500/60",
  orange: "from-orange-500/10 to-transparent hover:border-orange-500/60",
  cyan: "from-cyan-500/10 to-transparent hover:border-cyan-500/60",
  teal: "from-teal-500/10 to-transparent hover:border-teal-500/60",
  green: "from-green-500/10 to-transparent hover:border-green-500/60",
  purple: "from-purple-500/10 to-transparent hover:border-purple-500/60",
};

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
        ✨ 办公模板 · 点一下，填空就能用
      </div>
      <div className="scrollbar-hide -mx-1 flex gap-2 overflow-x-auto px-1 pb-1 sm:grid sm:grid-cols-3 sm:overflow-visible lg:grid-cols-4">
        {TEMPLATES.map((template) => {
          const theme = getSkill(template.skill).theme;
          return (
            <button
              key={template.id}
              type="button"
              onClick={() => handlePick(template)}
              className={cn(
                "bg-card flex w-40 shrink-0 cursor-pointer flex-col items-start gap-0.5 rounded-xl border bg-gradient-to-br px-3 py-2.5 text-left transition-colors sm:w-auto",
                CARD_THEME[theme],
              )}
            >
              <span className="flex items-center gap-1.5 text-sm font-medium">
                <span>{template.emoji}</span>
                <span>{template.name}</span>
              </span>
              <span className="text-muted-foreground text-xs">
                {template.scene}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
