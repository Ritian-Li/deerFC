// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { getToken } from "~/core/api/request";

// C 端产品：根路径直达卡密登录；已登录用户直接进聊天
export default function HomePage() {
  const router = useRouter();
  useEffect(() => {
    router.replace(getToken() ? "/chat" : "/login");
  }, [router]);
  return null;
}
