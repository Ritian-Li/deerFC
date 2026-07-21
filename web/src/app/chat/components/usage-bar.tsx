// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { ChevronDown, History } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

import { RenewForm } from "~/components/deer-flow/renew-form";
import { Button } from "~/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "~/components/ui/popover";
import { Separator } from "~/components/ui/separator";
import { refreshProfile, useProfile } from "~/core/store";
import { formatMonthDay } from "~/core/utils";
import { cn } from "~/lib/utils";

/**
 * Always-visible quota widget at the top of the chat page:
 * "剩余 N 次 · 有效期至 M/D · 当前模型：XX🔥".
 * Click to expand details and renew with a new code.
 */
export function UsageBar({ className }: { className?: string }) {
  const profile = useProfile();

  useEffect(() => {
    if (!profile) {
      void refreshProfile();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const lowQuota = (profile?.remaining_uses ?? 0) <= 0;
  const expired = profile?.expired ?? false;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className={cn(
            "bg-card hover:bg-accent flex h-8 max-w-[60vw] items-center gap-1 rounded-full border px-3 text-xs whitespace-nowrap transition-colors sm:text-sm",
            className,
          )}
        >
          {profile ? (
            <>
              <span
                className={cn(
                  "font-medium",
                  (lowQuota || expired) && "text-destructive",
                )}
              >
                {expired ? "已过期" : `剩余 ${profile.remaining_uses} 次`}
              </span>
              <span className="text-muted-foreground hidden sm:inline">
                · 至 {formatMonthDay(profile.expires_at)}
              </span>
              <span className="text-muted-foreground hidden truncate md:inline">
                · {profile.model}🔥
              </span>
            </>
          ) : (
            <span className="text-muted-foreground">余量加载中…</span>
          )}
          <ChevronDown className="size-3 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 max-w-[92vw]">
        <div className="flex flex-col gap-3">
          <div className="text-sm font-medium">我的卡密</div>
          {profile ? (
            <div className="text-muted-foreground flex flex-col gap-1.5 text-sm">
              <div className="flex justify-between">
                <span>剩余次数</span>
                <span
                  className={cn(
                    "text-foreground font-medium",
                    lowQuota && "text-destructive",
                  )}
                >
                  {profile.remaining_uses} 次
                </span>
              </div>
              <div className="flex justify-between">
                <span>有效期至</span>
                <span
                  className={cn(
                    "text-foreground",
                    expired && "text-destructive font-medium",
                  )}
                >
                  {formatMonthDay(profile.expires_at)}
                  {expired && "（已过期）"}
                </span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="shrink-0">当前模型</span>
                <span className="text-foreground truncate">
                  {profile.model}
                  {profile.provider ? ` · ${profile.provider}` : ""}🔥
                </span>
              </div>
            </div>
          ) : (
            <div className="text-muted-foreground text-sm">加载中…</div>
          )}
          <Separator />
          <div className="flex flex-col gap-2">
            <div className="text-sm font-medium">输入新卡密续费</div>
            <p className="text-muted-foreground text-xs">
              次数不够或快到期了？联系卖家购买新卡密，输入后立即生效。
            </p>
            <RenewForm />
          </div>
          <Separator />
          <Button
            className="w-full justify-start"
            variant="ghost"
            size="sm"
            asChild
          >
            <Link href="/tasks">
              <History className="size-4" />
              任务历史 / 找回结果
            </Link>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
