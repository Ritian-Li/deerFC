// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { ApiError } from "~/core/api";
import { isLoggedIn, login } from "~/core/store";

export default function LoginPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Already logged in? Go straight to chat. (An expired token will be
  // cleared by the global 401 interceptor and bounce back here.)
  useEffect(() => {
    if (isLoggedIn()) {
      router.replace("/chat");
    }
  }, [router]);

  const handleSubmit = useCallback(async () => {
    // Keep dashes as-is; only strip whitespace/newlines from pasting.
    const normalized = code.replace(/\s+/g, "");
    if (!normalized || submitting) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const { isNew } = await login(normalized);
      toast.success(isNew ? "卡密已激活，欢迎使用！" : "欢迎回来！");
      router.replace("/chat");
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.detail || "登录失败，请稍后重试");
      } else {
        setError("网络开小差了，请检查网络后重试");
      }
      setSubmitting(false);
    }
  }, [code, submitting, router]);

  return (
    <div className="bg-app flex min-h-screen w-full flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="mb-10 flex flex-col items-center text-center">
          <div className="mb-3 text-6xl">🔍</div>
          <h1 className="text-2xl font-semibold">AI 深度研究助手</h1>
          <p className="text-muted-foreground mt-3 text-sm leading-relaxed">
            输入卡密开始使用，首次输入自动激活
          </p>
        </div>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void handleSubmit();
          }}
        >
          <Input
            className="h-12 text-center text-base tracking-wider"
            value={code}
            placeholder="粘贴卡密，如 XXXX-XXXX-XXXX"
            autoFocus
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
            enterKeyHint="go"
            onChange={(event) => {
              setCode(event.target.value);
              setError(null);
            }}
          />
          {error && (
            <p className="text-destructive text-center text-sm">{error}</p>
          )}
          <Button
            className="h-12 w-full text-base"
            type="submit"
            disabled={submitting || code.replace(/\s+/g, "") === ""}
          >
            {submitting && <LoaderCircle className="size-4 animate-spin" />}
            {submitting ? "正在进入…" : "进入"}
          </Button>
        </form>
        <p className="text-muted-foreground mt-8 text-center text-xs leading-relaxed">
          还没有卡密？请联系卖家购买。
          <br />
          卡密支持带横杠直接粘贴，多余空格会自动去掉。
        </p>
      </div>
    </div>
  );
}
