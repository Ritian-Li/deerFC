// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { ArrowLeft, Download, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { AuthGuard } from "~/components/deer-flow/auth-guard";
import { Markdown } from "~/components/deer-flow/markdown";
import { Button } from "~/components/ui/button";
import { Card, CardContent } from "~/components/ui/card";
import {
  ApiError,
  downloadRunFile,
  getRun,
  type RunDetail,
} from "~/core/api";
import { formatDateTime } from "~/core/utils";

import { skillLabel, StatusBadge } from "../shared";

export default function TaskDetailPage() {
  return (
    <AuthGuard>
      <TaskDetail />
    </AuthGuard>
  );
}

function TaskDetail() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!runId) {
      return;
    }
    getRun(runId)
      .then(setRun)
      .catch((error) => {
        setLoadFailed(true);
        if (error instanceof ApiError && error.status !== 401) {
          toast.error(error.detail || "加载任务详情失败，请返回重试");
        }
      });
  }, [runId]);

  const handleDownload = useCallback(async () => {
    if (!runId || downloading) {
      return;
    }
    setDownloading(true);
    try {
      await downloadRunFile(runId);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        toast("这个任务没有可下载的文件");
      } else if (error instanceof ApiError && error.status !== 401) {
        toast.error(error.detail || "下载失败，请稍后重试");
      } else if (!(error instanceof ApiError)) {
        toast.error("网络开小差了，请稍后重试");
      }
    } finally {
      setDownloading(false);
    }
  }, [runId, downloading]);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-3 pt-3 pb-12 sm:px-4">
      <header className="mb-4 flex items-center gap-2">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/tasks">
            <ArrowLeft />
          </Link>
        </Button>
        <h1 className="flex-grow truncate text-lg font-medium">
          {run ? skillLabel(run.skill) : "任务详情"}
        </h1>
        {run && <StatusBadge status={run.status} />}
      </header>
      {!run && !loadFailed && (
        <div className="text-muted-foreground flex flex-grow items-center justify-center py-24 text-sm">
          <LoaderCircle className="mr-2 size-4 animate-spin" />
          加载中…
        </div>
      )}
      {loadFailed && (
        <div className="text-muted-foreground flex flex-col items-center gap-3 py-24 text-sm">
          加载失败了，请返回列表重试。
          <Button variant="outline" asChild>
            <Link href="/tasks">返回任务历史</Link>
          </Button>
        </div>
      )}
      {run && (
        <div className="flex flex-col gap-4">
          <Card>
            <CardContent className="flex flex-col gap-2 px-4 py-1">
              <div className="text-sm font-medium">调用回执</div>
              <div className="text-muted-foreground grid grid-cols-1 gap-x-4 gap-y-1 text-xs sm:grid-cols-2 sm:text-sm">
                <span>
                  模型：
                  <span className="text-foreground">
                    {run.receipt?.model ?? "-"}
                  </span>
                </span>
                <span>
                  Token 消耗：
                  <span className="text-foreground">
                    {run.receipt?.total_tokens?.toLocaleString() ?? "-"}
                  </span>
                </span>
                <span>
                  开始时间：
                  <span className="text-foreground">
                    {formatDateTime(run.receipt?.created_at)}
                  </span>
                </span>
                <span>
                  结束时间：
                  <span className="text-foreground">
                    {formatDateTime(run.receipt?.finished_at)}
                  </span>
                </span>
                <span>
                  是否扣次：
                  <span className="text-foreground">
                    {run.charged ? "已扣 1 次" : "未扣次数"}
                  </span>
                </span>
              </div>
              <div className="mt-1">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={downloading}
                  onClick={() => void handleDownload()}
                >
                  {downloading ? (
                    <LoaderCircle className="size-4 animate-spin" />
                  ) : (
                    <Download className="size-4" />
                  )}
                  下载文件（PPT 等）
                </Button>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="px-4 py-1">
              {run.result_md ? (
                <Markdown>{run.result_md}</Markdown>
              ) : (
                <div className="text-muted-foreground py-8 text-center text-sm">
                  {run.status === "running"
                    ? "任务还在进行中，稍后回来查看结果哦"
                    : "这个任务没有文字结果"}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
