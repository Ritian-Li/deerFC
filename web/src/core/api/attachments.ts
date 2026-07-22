// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import {
  ApiError,
  authHeaders,
  clearToken,
  extractErrorDetail,
  notifyPaymentRequired,
  redirectToLogin,
} from "./request";
import { resolveServiceURL } from "./resolve-service-url";

export interface AttachmentMeta {
  id: string;
  name: string;
  kind: "image" | "document";
  chars: number;
  /** Non-empty when the backend saved the file but failed to parse it. */
  error: string;
}

/**
 * Upload one attachment (multipart). Free of charge — does not consume quota.
 * Mirrors authFetch's 401/402 handling, but must NOT set Content-Type:
 * the browser generates the multipart boundary itself.
 */
export async function uploadAttachment(file: File): Promise<AttachmentMeta> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(resolveServiceURL("attachments"), {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    if (response.status === 401) {
      clearToken();
      redirectToLogin();
      throw new ApiError(401, "登录已失效，请重新输入卡密");
    }
    if (response.status === 402) {
      notifyPaymentRequired();
      throw new ApiError(402, detail || "剩余次数不足");
    }
    if (response.status === 413) {
      throw new ApiError(413, "文件过大，单个文件不能超过 15MB");
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as AttachmentMeta;
}
