// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";

import { SKILLS } from "~/core/skills";
import { setCurrentSkill, useCurrentSkill } from "~/core/store";
import { cn } from "~/lib/utils";

import { Welcome } from "./welcome";

export function ConversationStarter({
  className,
  onFillExample,
}: {
  className?: string;
  /** Select the skill and fill the example text into the input (no auto-send). */
  onFillExample?: (message: string) => void;
}) {
  const currentSkill = useCurrentSkill();

  return (
    <div className={cn("flex w-full flex-col items-center", className)}>
      <div className="pointer-events-none fixed inset-0 flex items-center justify-center">
        <Welcome className="pointer-events-auto mb-15 w-[75%] -translate-y-36" />
      </div>
      <div className="flex w-full flex-col gap-3">
        {/* Skill entries with example prompts. Click an example to fill it in. */}
        <div className="scrollbar-hide flex gap-2 overflow-x-auto pb-1">
          {SKILLS.map((skill) => {
            const active = skill.id === currentSkill;
            return (
              <button
                key={skill.id}
                type="button"
                onClick={() => setCurrentSkill(skill.id)}
                className={cn(
                  "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm whitespace-nowrap transition-colors",
                  active
                    ? "border-brand bg-brand/10 text-brand font-medium"
                    : "bg-card text-muted-foreground hover:bg-accent",
                )}
                aria-pressed={active}
              >
                <span>{skill.emoji}</span>
                <span>{skill.name}</span>
              </button>
            );
          })}
        </div>
        <ul className="flex flex-wrap">
          {SKILLS.flatMap((skill) =>
            skill.subSkills[0]!.examples.slice(0, 1).map((example) => ({
              skill,
              example,
            })),
          ).map(({ skill, example }, index) => (
            <motion.li
              key={`${skill.id}-${example}`}
              className="flex w-1/2 shrink-0 p-2 active:scale-105"
              style={{ transition: "all 0.2s ease-out" }}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{
                duration: 0.2,
                delay: index * 0.1 + 0.3,
                ease: "easeOut",
              }}
            >
              <div
                className="bg-card text-muted-foreground flex min-w-0 cursor-pointer flex-col gap-1 rounded-2xl border px-4 py-3 opacity-75 transition-all duration-300 hover:opacity-100 hover:shadow-md"
                onClick={() => {
                  setCurrentSkill(skill.id);
                  onFillExample?.(example);
                }}
              >
                <span className="text-foreground text-xs font-medium">
                  {skill.emoji} {skill.name}
                </span>
                <span className="text-sm">{example}</span>
              </div>
            </motion.li>
          ))}
        </ul>
      </div>
    </div>
  );
}
