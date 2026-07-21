// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { isLoggedIn, refreshProfile } from "~/core/store";

import { RenewDialog } from "./renew-dialog";

/**
 * Client-side auth guard: redirects to /login when no token is stored.
 * Also mounts the global 402 renew dialog for all protected pages.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    setReady(true);
    void refreshProfile();
  }, [router]);

  if (!ready) {
    return (
      <div className="text-muted-foreground flex h-screen w-screen items-center justify-center">
        加载中…
      </div>
    );
  }
  return (
    <>
      {children}
      <RenewDialog />
    </>
  );
}
