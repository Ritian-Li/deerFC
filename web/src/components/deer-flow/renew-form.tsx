// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { LoaderCircle } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { ApiError } from "~/core/api";
import { renew } from "~/core/store";
import { cn } from "~/lib/utils";

/**
 * "输入新卡密续费" form, shared by the usage bar popover and the
 * out-of-quota (402) dialog.
 */
export function RenewForm({
  className,
  autoFocus,
  onSuccess,
}: {
  className?: string;
  autoFocus?: boolean;
  onSuccess?: () => void;
}) {
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = useCallback(async () => {
    const normalized = code.replace(/\s+/g, "");
    if (!normalized || submitting) {
      return;
    }
    setSubmitting(true);
    try {
      await renew(normalized);
      toast.success("续费成功，次数和有效期已更新");
      setCode("");
      onSuccess?.();
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 400) {
          toast.error("这个卡密无效或已被使用，请核对后重试");
        } else if (error.status === 429) {
          toast.error("操作有点频繁，请稍等片刻再试");
        } else {
          toast.error(error.detail || "续费失败，请稍后重试");
        }
      } else {
        toast.error("网络开小差了，请稍后重试");
      }
    } finally {
      setSubmitting(false);
    }
  }, [code, submitting, onSuccess]);

  return (
    <form
      className={cn("flex w-full items-center gap-2", className)}
      onSubmit={(event) => {
        event.preventDefault();
        void handleSubmit();
      }}
    >
      <Input
        className="h-10 flex-grow text-base md:text-sm"
        value={code}
        placeholder="粘贴新卡密，如 XXXX-XXXX-XXXX"
        autoFocus={autoFocus}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck={false}
        onChange={(event) => setCode(event.target.value)}
      />
      <Button
        className="h-10 shrink-0"
        type="submit"
        disabled={submitting || code.replace(/\s+/g, "") === ""}
      >
        {submitting && <LoaderCircle className="size-4 animate-spin" />}
        续费
      </Button>
    </form>
  );
}
