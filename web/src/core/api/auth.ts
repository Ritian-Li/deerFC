// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { ApiError, authFetch, extractErrorDetail } from "./request";
import { resolveServiceURL } from "./resolve-service-url";

export interface UserProfile {
  user_id: string;
  remaining_uses: number;
  expires_at: string;
  expired: boolean;
  model: string;
  provider: string;
}

export interface SessionResponse {
  token: string;
  is_new: boolean;
  profile: UserProfile;
}

/**
 * Exchange an access code for a session token.
 * Unauthenticated: 401 = invalid code, 429 = too many attempts.
 */
export async function createSession(code: string): Promise<SessionResponse> {
  const response = await fetch(resolveServiceURL("auth/session"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    if (response.status === 401) {
      throw new ApiError(401, "卡密无效，请核对后重新输入");
    }
    if (response.status === 429) {
      throw new ApiError(429, "尝试次数太多啦，请稍等一会儿再试");
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<SessionResponse>;
}

/** Redeem a new code onto the current account. 400 = invalid/used code. */
export async function renewSession(
  code: string,
): Promise<{ profile: UserProfile }> {
  const response = await authFetch("auth/renew", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
  return response.json() as Promise<{ profile: UserProfile }>;
}

export async function fetchMe(): Promise<{ profile: UserProfile }> {
  const response = await authFetch("auth/me");
  return response.json() as Promise<{ profile: UserProfile }>;
}
