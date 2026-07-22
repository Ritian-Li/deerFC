// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import type { PreviewKind, SkillTheme } from "~/core/skills";
import { cn } from "~/lib/utils";

/**
 * 纯 CSS 绘制的「成品缩略预览」：让子能力/模板卡直接长得像最终交付物
 * （A4 文档、表格、幻灯片、试卷…），而不是 emoji 色块。
 * 零图片资源、零请求，深浅色主题自适应。
 */

/** 主题色的静态 tailwind 类（JIT 需要字面量）。 */
const ACCENT: Record<SkillTheme, { solid: string; soft: string }> = {
  blue: { solid: "bg-blue-500", soft: "bg-blue-500/25" },
  orange: { solid: "bg-orange-500", soft: "bg-orange-500/25" },
  cyan: { solid: "bg-cyan-500", soft: "bg-cyan-500/25" },
  teal: { solid: "bg-teal-500", soft: "bg-teal-500/25" },
  green: { solid: "bg-green-500", soft: "bg-green-500/25" },
  purple: { solid: "bg-purple-500", soft: "bg-purple-500/25" },
};

/** 正文灰线（纸面上的"文字"）。 */
const INK = "bg-zinc-400/80";
const INK_STRONG = "bg-zinc-600";

function Line({ w, strong = false }: { w: string; strong?: boolean }) {
  return <div className={cn("h-[3px] rounded-full", w, strong ? INK_STRONG : INK)} />;
}

function Paper({
  landscape = false,
  children,
  className,
}: {
  landscape?: boolean;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex h-full flex-col overflow-hidden rounded-[4px] border border-black/10 bg-white shadow-sm dark:border-black/20 dark:bg-zinc-50",
        landscape ? "aspect-[16/10]" : "aspect-[3/4]",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function MiniPreview({
  kind,
  theme,
  className,
}: {
  kind: PreviewKind;
  theme: SkillTheme;
  className?: string;
}) {
  const accent = ACCENT[theme];
  const body = (() => {
    switch (kind) {
      case "report":
        return (
          <Paper className="gap-1 p-1.5">
            <Line w="w-3/5" strong />
            <div className={cn("h-[2px] w-2/5 rounded-full", accent.solid)} />
            <div className="mt-0.5 flex flex-col gap-1">
              <Line w="w-full" />
              <Line w="w-full" />
              <Line w="w-4/5" />
              <Line w="w-full" />
              <Line w="w-2/3" />
            </div>
          </Paper>
        );
      case "chart":
        return (
          <Paper className="gap-1 p-1.5">
            <Line w="w-1/2" strong />
            <div className="mt-0.5 flex h-7 items-end gap-1 px-0.5">
              {["h-2", "h-4", "h-3", "h-6", "h-5"].map((h, i) => (
                <div key={i} className={cn("w-full rounded-sm", h, accent.solid, i % 2 && accent.soft)} />
              ))}
            </div>
            <Line w="w-full" />
            <Line w="w-3/4" />
          </Paper>
        );
      case "swot":
        return (
          <Paper className="gap-1 p-1.5">
            <Line w="w-1/2" strong />
            <div className="mt-0.5 grid grow grid-cols-2 gap-0.5">
              <div className={cn("rounded-sm", accent.soft)} />
              <div className="rounded-sm bg-zinc-200" />
              <div className="rounded-sm bg-zinc-200" />
              <div className={cn("rounded-sm", accent.soft)} />
            </div>
            <Line w="w-2/3" />
          </Paper>
        );
      case "cite":
        return (
          <Paper className="gap-1 p-1.5">
            <Line w="w-3/5" strong />
            <div className="mt-0.5 flex flex-col gap-1">
              <Line w="w-full" />
              <div className="pl-2"><Line w="w-4/5" /></div>
              <Line w="w-full" />
              <div className="pl-2"><Line w="w-3/4" /></div>
              <div className="pl-2"><Line w="w-2/3" /></div>
            </div>
          </Paper>
        );
      case "clauses":
        return (
          <Paper className="items-center gap-1 p-1.5">
            <Line w="w-1/2" strong />
            <div className="mt-0.5 flex w-full flex-col gap-1">
              {["w-full", "w-5/6", "w-full", "w-2/3"].map((w, i) => (
                <div key={i} className="flex items-center gap-1">
                  <div className={cn("h-[5px] w-[5px] shrink-0 rounded-full", accent.solid)} />
                  <Line w={w} />
                </div>
              ))}
            </div>
          </Paper>
        );
      case "slide":
        return (
          <Paper landscape className="justify-center gap-1.5 p-2">
            <div className={cn("h-1 w-1/3 rounded-full", accent.solid)} />
            <Line w="w-3/5" strong />
            <Line w="w-2/5" />
          </Paper>
        );
      case "slide-chart":
        return (
          <Paper landscape className="gap-1 p-2">
            <Line w="w-1/2" strong />
            <div className="flex grow items-end gap-1 px-1 pb-0.5">
              {["h-2", "h-3.5", "h-2.5", "h-5"].map((h, i) => (
                <div key={i} className={cn("w-full rounded-sm", h, accent.solid)} />
              ))}
            </div>
          </Paper>
        );
      case "slide-steps":
        return (
          <Paper landscape className="justify-center gap-1 p-2">
            <Line w="w-1/2" strong />
            {["w-4/5", "w-3/5", "w-2/3"].map((w, i) => (
              <div key={i} className="flex items-center gap-1">
                <div className={cn("h-[5px] w-[5px] shrink-0 rounded-full", accent.solid)} />
                <Line w={w} />
              </div>
            ))}
          </Paper>
        );
      case "slide-hero":
        return (
          <Paper landscape className="items-center justify-center gap-1.5 p-2">
            <div className={cn("h-2 w-2/3 rounded-sm", accent.solid)} />
            <Line w="w-1/2" />
          </Paper>
        );
      case "checklist":
        return (
          <Paper className="gap-1 p-1.5">
            <Line w="w-1/2" strong />
            <div className="mt-0.5 flex flex-col gap-1">
              {["w-4/5", "w-full", "w-2/3", "w-3/4"].map((w, i) => (
                <div key={i} className="flex items-center gap-1">
                  <div className={cn("h-[5px] w-[5px] shrink-0 rounded-[1px]", accent.solid)} />
                  <Line w={w} />
                </div>
              ))}
            </div>
          </Paper>
        );
      case "minutes":
        return (
          <Paper className="gap-1 p-1.5">
            <Line w="w-1/2" strong />
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-1">
                <div className={cn("h-[3px] w-1/4 shrink-0 rounded-full", accent.solid)} />
                <Line w="w-full" />
              </div>
            ))}
            <div className="mt-auto flex items-center gap-1">
              <div className={cn("h-[5px] w-[5px] rounded-full", accent.solid)} />
              <Line w="w-1/2" strong />
            </div>
          </Paper>
        );
      case "timeline":
        return (
          <Paper className="flex-row gap-1.5 p-1.5">
            <div className="flex flex-col items-center gap-0.5 pt-0.5">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex flex-col items-center">
                  <div className={cn("h-[5px] w-[5px] rounded-full", accent.solid)} />
                  {i < 3 && <div className={cn("h-3 w-[2px]", accent.soft)} />}
                </div>
              ))}
            </div>
            <div className="flex grow flex-col gap-2 pt-0.5">
              <Line w="w-4/5" strong />
              <Line w="w-full" />
              <Line w="w-2/3" />
            </div>
          </Paper>
        );
      case "notice":
        return (
          <Paper className="items-center gap-1 p-1.5">
            {/* 红头文件 */}
            <div className="h-[4px] w-2/3 rounded-full bg-red-500/80" />
            <div className="h-[2px] w-full bg-red-500/40" />
            <div className="mt-0.5 flex w-full flex-col gap-1">
              <Line w="w-full" />
              <Line w="w-4/5" />
              <Line w="w-full" />
            </div>
            <div className="mt-auto flex w-full justify-end">
              <Line w="w-1/3" />
            </div>
          </Paper>
        );
      case "resume":
        return (
          <Paper className="gap-1 p-1.5">
            <div className="flex items-center gap-1.5">
              <div className={cn("h-4 w-3.5 shrink-0 rounded-[2px]", accent.soft)} />
              <div className="flex grow flex-col gap-1">
                <Line w="w-2/3" strong />
                <Line w="w-1/2" />
              </div>
            </div>
            <div className={cn("mt-0.5 h-[2px] w-full rounded-full", accent.solid)} />
            <Line w="w-full" />
            <Line w="w-4/5" />
            <Line w="w-full" />
          </Paper>
        );
      case "grid":
      case "grid-status":
      case "grid-total":
        return (
          <Paper landscape className="p-1.5">
            <div className="grid h-full w-full grid-cols-4 grid-rows-4 gap-[2px]">
              {Array.from({ length: 16 }, (_, i) => {
                const isHeader = i < 4;
                const isTotal = kind === "grid-total" && i >= 12;
                const statusCell = kind === "grid-status" && i % 4 === 3 && i >= 4;
                return (
                  <div
                    key={i}
                    className={cn(
                      "flex items-center justify-center rounded-[1px]",
                      isHeader
                        ? accent.solid
                        : isTotal
                          ? accent.soft
                          : "bg-zinc-200/90",
                    )}
                  >
                    {statusCell && (
                      <div className={cn("h-[5px] w-[5px] rounded-full", accent.solid)} />
                    )}
                  </div>
                );
              })}
            </div>
          </Paper>
        );
      case "exam":
        return (
          <Paper className="gap-1 p-1.5">
            <div className="flex items-start justify-between">
              <div className="flex w-2/3 flex-col items-center gap-1 pl-2">
                <Line w="w-full" strong />
              </div>
              <div className="h-3 w-4 rounded-[1px] border border-zinc-400/80" />
            </div>
            <div className="flex items-center gap-1">
              <div className={cn("h-[3px] w-2 rounded-full", accent.solid)} />
              <Line w="w-3/5" />
            </div>
            <div className="flex gap-1 pl-2">
              {["A", "B", "C"].map((o) => (
                <div key={o} className="flex items-center gap-0.5">
                  <div className="h-[5px] w-[5px] rounded-full border border-zinc-400/80" />
                  <div className={cn("h-[3px] w-2 rounded-full", INK)} />
                </div>
              ))}
            </div>
            <div className="flex items-center gap-1">
              <div className={cn("h-[3px] w-2 rounded-full", accent.solid)} />
              <Line w="w-4/5" />
            </div>
            <Line w="w-1/2" />
          </Paper>
        );
      case "lesson":
        return (
          <Paper className="gap-1 p-1.5">
            <Line w="w-1/2" strong />
            {[1, 2].map((i) => (
              <div key={i} className="flex flex-col gap-1">
                <div className="flex items-center gap-1">
                  <div className={cn("h-[3px] w-3 rounded-full", accent.solid)} />
                </div>
                <div className="pl-2">
                  <Line w="w-4/5" />
                </div>
              </div>
            ))}
            <Line w="w-2/3" />
          </Paper>
        );
    }
  })();

  return (
    <div className={cn("flex items-center justify-center", className)}>{body}</div>
  );
}
