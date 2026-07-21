// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { History } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Suspense } from "react";

import { AuthGuard } from "~/components/deer-flow/auth-guard";
import { Button } from "~/components/ui/button";

import { Logo } from "../../components/deer-flow/logo";
import { ThemeToggle } from "../../components/deer-flow/theme-toggle";
import { Tooltip } from "../../components/deer-flow/tooltip";
import { SettingsDialog } from "../settings/dialogs/settings-dialog";

import { UsageBar } from "./components/usage-bar";

const Main = dynamic(() => import("./main"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center">
      Loading DeerFlow...
    </div>
  ),
});

export default function HomePage() {
  return (
    <AuthGuard>
      <div className="flex h-screen w-screen justify-center overscroll-none">
        <header className="bg-app/80 fixed top-0 left-0 z-40 flex h-12 w-full items-center justify-between px-2 backdrop-blur-lg sm:px-4">
          <div className="hidden sm:block">
            <Logo />
          </div>
          <div className="flex w-full items-center justify-between gap-1 sm:w-auto sm:justify-end">
            <UsageBar />
            <div className="flex items-center">
              <Tooltip title="任务历史">
                <Button variant="ghost" size="icon" asChild>
                  <Link href="/tasks">
                    <History />
                  </Link>
                </Button>
              </Tooltip>
              <ThemeToggle />
              <Suspense>
                <SettingsDialog />
              </Suspense>
            </div>
          </div>
        </header>
        <Main />
      </div>
    </AuthGuard>
  );
}
