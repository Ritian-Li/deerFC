// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { create } from "zustand";

import {
  createSession,
  fetchMe,
  renewSession,
  type UserProfile,
} from "../api/auth";
import {
  clearToken,
  getToken,
  setPaymentRequiredHandler,
  setToken,
} from "../api/request";

export const useAuthStore = create<{
  profile: UserProfile | null;
  /** Whether the "out of quota, please renew" dialog is open (402). */
  renewDialogOpen: boolean;
}>(() => ({
  profile: null,
  renewDialogOpen: false,
}));

// Pop the renew dialog whenever any API call returns 402.
setPaymentRequiredHandler(() => {
  useAuthStore.setState({ renewDialogOpen: true });
});

export function isLoggedIn() {
  return getToken() != null;
}

export async function login(code: string) {
  const { token, is_new, profile } = await createSession(code);
  setToken(token);
  useAuthStore.setState({ profile });
  return { isNew: is_new, profile };
}

export function logout() {
  clearToken();
  useAuthStore.setState({ profile: null });
}

export async function refreshProfile() {
  try {
    const { profile } = await fetchMe();
    useAuthStore.setState({ profile });
    return profile;
  } catch {
    // Network hiccups shouldn't break the page; 401 is already
    // handled globally (redirect to /login).
    return null;
  }
}

export async function renew(code: string) {
  const { profile } = await renewSession(code);
  useAuthStore.setState({ profile, renewDialogOpen: false });
  return profile;
}

/** Sync remaining uses pushed by run_complete / run_error stream events. */
export function setRemainingUses(remainingUses: number | undefined) {
  if (typeof remainingUses !== "number") {
    return;
  }
  useAuthStore.setState((state) =>
    state.profile
      ? { profile: { ...state.profile, remaining_uses: remainingUses } }
      : {},
  );
}

export function openRenewDialog() {
  useAuthStore.setState({ renewDialogOpen: true });
}

export function closeRenewDialog() {
  useAuthStore.setState({ renewDialogOpen: false });
}

export function useProfile() {
  return useAuthStore((state) => state.profile);
}
