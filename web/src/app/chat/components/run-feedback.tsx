// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { motion } from "framer-motion";
import { CircleCheck, ShieldCheck } from "lucide-react";

import { Card, CardContent } from "~/components/ui/card";
import { useStore } from "~/core/store";
import { formatDuration } from "~/core/utils";
import { cn } from "~/lib/utils";

/**
 * Rendered after a run ends:
 * - run_complete → 调用回执 (model / provider / tokens / duration)
 * - run_error → friendly error card highlighting "未扣除次数"
 */
export function RunFeedback({ className }: { className?: string }) {
  const receipt = useStore((state) => state.lastReceipt);
  const runError = useStore((state) => state.lastRunError);
  const responding = useStore((state) => state.responding);

  if (responding || (!receipt && !runError)) {
    return null;
  }

  return (
    <motion.div
      className={cn("w-full", className)}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {runError ? (
        <Card className="w-full border-amber-500/40 bg-amber-500/5">
          <CardContent className="flex flex-col gap-2 px-4 py-1">
            <div className="flex items-center gap-2 text-sm font-medium text-amber-600 dark:text-amber-400">
              <ShieldCheck className="size-4 shrink-0" />
              任务没有完成
            </div>
            <p className="text-sm leading-relaxed">{runError}</p>
            <p className="text-muted-foreground text-xs">
              放心，<span className="text-foreground font-medium">未扣除次数</span>
              ，稍后再试一次就好。
            </p>
          </CardContent>
        </Card>
      ) : receipt ? (
        <Card className="w-full">
          <CardContent className="flex flex-col gap-2 px-4 py-1">
            <div className="flex items-center gap-2 text-sm font-medium text-green-600 dark:text-green-400">
              <CircleCheck className="size-4 shrink-0" />
              任务完成 · 调用回执
            </div>
            <div className="text-muted-foreground grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:text-sm">
              <span>
                模型：<span className="text-foreground">{receipt.model}</span>
              </span>
              {receipt.provider && (
                <span>
                  平台：
                  <span className="text-foreground">{receipt.provider}</span>
                </span>
              )}
              <span>
                Token 消耗：
                <span className="text-foreground">
                  {receipt.total_tokens?.toLocaleString?.() ??
                    receipt.total_tokens}
                </span>
              </span>
              {receipt.duration_ms != null && (
                <span>
                  耗时：
                  <span className="text-foreground">
                    {formatDuration(receipt.duration_ms)}
                  </span>
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      ) : null}
    </motion.div>
  );
}
