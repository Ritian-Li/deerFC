// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

export function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Format an ISO date as "M/D" (e.g. 8/20). */
export function formatMonthDay(iso: string | null | undefined) {
  if (!iso) {
    return "-";
  }
  const date = new Date(iso);
  if (isNaN(date.getTime())) {
    return "-";
  }
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

/** Format an ISO date as "M月D日 HH:mm". */
export function formatDateTime(iso: string | null | undefined) {
  if (!iso) {
    return "-";
  }
  const date = new Date(iso);
  if (isNaN(date.getTime())) {
    return "-";
  }
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${date.getMonth() + 1}月${date.getDate()}日 ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** Format a millisecond duration as a friendly string (e.g. 2分15秒). */
export function formatDuration(ms: number | null | undefined) {
  if (ms == null || isNaN(ms) || ms < 0) {
    return "-";
  }
  const totalSeconds = Math.round(ms / 1000);
  if (totalSeconds < 60) {
    return `${totalSeconds}秒`;
  }
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return seconds > 0 ? `${minutes}分${seconds}秒` : `${minutes}分钟`;
}
