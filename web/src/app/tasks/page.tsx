// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { ArrowLeft, ChevronRight, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { AuthGuard } from "~/components/deer-flow/auth-guard";
import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import { ApiError, listRuns, type RunSummary } from "~/core/api";
import { formatDateTime } from "~/core/utils";

import { skillLabel, StatusBadge } from "./shared";

export default function TasksPage() {
  return (
    <AuthGuard>
      <TasksList />
    </AuthGuard>
  );
}

function TasksList() {
  const router = useRouter();
  const [runs, setRuns] = useState<RunSummary[] | null>(null);

  useEffect(() => {
    listRuns()
      .then(setRuns)
      .catch((error) => {
        setRuns([]);
        if (error instanceof ApiError && error.status !== 401) {
          toast.error(error.detail || "加载任务历史失败，请刷新重试");
        }
      });
  }, []);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-3 pt-3 pb-8 sm:px-4">
      <header className="mb-4 flex items-center gap-2">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/chat">
            <ArrowLeft />
          </Link>
        </Button>
        <h1 className="text-lg font-medium">任务历史</h1>
      </header>
      {runs === null ? (
        <div className="text-muted-foreground flex flex-grow items-center justify-center py-24 text-sm">
          <LoaderCircle className="mr-2 size-4 animate-spin" />
          加载中…
        </div>
      ) : runs.length === 0 ? (
        <div className="text-muted-foreground flex flex-col items-center gap-3 py-24 text-sm">
          <div className="text-4xl">🦌</div>
          还没有任务记录，去发起你的第一次研究吧！
          <Button asChild>
            <Link href="/chat">去提问</Link>
          </Button>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {runs.map((run) => (
            <li key={run.run_id}>
              <Card
                className="hover:bg-accent/50 flex cursor-pointer flex-col gap-2 px-4 py-1 transition-colors"
                onClick={() => router.push(`/tasks/${run.run_id}`)}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="truncate font-medium">
                    {skillLabel(run.skill)}
                  </div>
                  <StatusBadge status={run.status} />
                </div>
                <div className="text-muted-foreground flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                  <span>{formatDateTime(run.created_at)}</span>
                  <span>{run.charged ? "已扣 1 次" : "未扣次数"}</span>
                  {run.total_tokens != null && (
                    <span>{run.total_tokens.toLocaleString()} tokens</span>
                  )}
                  {run.model && <span>{run.model}</span>}
                  <span className="text-muted-foreground/60 ml-auto flex items-center">
                    查看
                    <ChevronRight className="size-3.5" />
                  </span>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
