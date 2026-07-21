// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { resolveServiceURL } from "./resolve-service-url";

const TOKEN_KEY = "deerflow.token";

export function getToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function redirectToLogin() {
  if (typeof window !== "undefined" && !location.pathname.startsWith("/login")) {
    location.href = "/login";
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

/**
 * Handler invoked whenever the server responds with 402 (out of quota).
 * Registered by the auth store to pop up the renew dialog.
 */
let paymentRequiredHandler: (() => void) | null = null;
export function setPaymentRequiredHandler(handler: () => void) {
  paymentRequiredHandler = handler;
}
export function notifyPaymentRequired() {
  paymentRequiredHandler?.();
}

export async function extractErrorDetail(
  response: Response,
  fallback?: string,
): Promise<string> {
  try {
    const body: unknown = await response.clone().json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string" && detail) {
        return detail;
      }
    }
  } catch {
    // ignore body parse errors
  }
  return fallback ?? `请求失败（${response.status}）`;
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Fetch wrapper for authenticated JSON API calls.
 * - Attaches the Bearer token.
 * - On 401 clears the token and redirects to /login.
 * - On 402 triggers the global renew dialog.
 * - Throws ApiError with a friendly detail message otherwise.
 */
export async function authFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const response = await fetch(resolveServiceURL(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...((init.headers as Record<string, string>) ?? {}),
    },
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
    throw new ApiError(response.status, detail);
  }
  return response;
}
