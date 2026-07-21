// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { CircleCheck, CircleX, LoaderCircle } from "lucide-react";

import { Badge } from "~/components/ui/badge";
import type { RunStatus } from "~/core/api";

const SKILL_LABELS: Record<string, string> = {
  research: "深度研究",
  deep_research: "深度研究",
  ppt: "PPT 生成",
  podcast: "播客生成",
  prose: "文稿写作",
};

export function skillLabel(skill: string) {
  return SKILL_LABELS[skill] ?? skill;
}

export function StatusBadge({ status }: { status: RunStatus }) {
  if (status === "running") {
    return (
      <Badge
        variant="outline"
        className="border-blue-500/40 text-blue-600 dark:text-blue-400"
      >
        <LoaderCircle className="size-3 animate-spin" />
        进行中
      </Badge>
    );
  }
  if (status === "succeeded") {
    return (
      <Badge
        variant="outline"
        className="border-green-500/40 text-green-600 dark:text-green-400"
      >
        <CircleCheck className="size-3" />
        已完成
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="border-destructive/40 text-destructive">
      <CircleX className="size-3" />
      失败
    </Badge>
  );
}
