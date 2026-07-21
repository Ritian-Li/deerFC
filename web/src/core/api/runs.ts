// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { authFetch } from "./request";

export type RunStatus = "running" | "succeeded" | "failed";

export interface RunSummary {
  run_id: string;
  thread_id: string;
  skill: string;
  status: RunStatus;
  charged: boolean;
  created_at: string;
  finished_at: string | null;
  total_tokens: number | null;
  model: string | null;
  has_result: boolean;
}

export interface RunDetail {
  run_id: string;
  thread_id: string;
  skill: string;
  status: RunStatus;
  charged: boolean;
  result_md: string | null;
  receipt: {
    model: string | null;
    total_tokens: number | null;
    created_at: string | null;
    finished_at: string | null;
  } | null;
}

export async function listRuns(): Promise<RunSummary[]> {
  const response = await authFetch("runs");
  const data = (await response.json()) as { runs: RunSummary[] };
  return data.runs ?? [];
}

export async function getRun(runId: string): Promise<RunDetail> {
  const response = await authFetch(`runs/${runId}`);
  return response.json() as Promise<RunDetail>;
}

/**
 * Download the generated file (e.g. PPT) of a run and trigger a browser save.
 * Throws ApiError(404) when the run has no downloadable file.
 */
export async function downloadRunFile(runId: string): Promise<void> {
  const response = await authFetch(`runs/${runId}/file`);
  const blob = await response.blob();
  let filename = `deerflow-${runId}`;
  const disposition = response.headers.get("Content-Disposition");
  if (disposition) {
    const utf8Match = /filename\*=(?:UTF-8''|utf-8'')([^;]+)/i.exec(
      disposition,
    );
    const plainMatch = /filename="?([^";]+)"?/i.exec(disposition);
    if (utf8Match?.[1]) {
      try {
        filename = decodeURIComponent(utf8Match[1]);
      } catch {
        filename = utf8Match[1];
      }
    } else if (plainMatch?.[1]) {
      filename = plainMatch[1];
    }
  }
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
