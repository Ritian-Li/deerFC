// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";

import { cn } from "~/lib/utils";

export function Welcome({ className }: { className?: string }) {
  return (
    <motion.div
      className={cn("flex flex-col", className)}
      style={{ transition: "all 0.2s ease-out" }}
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <h3 className="mb-2 text-center text-3xl font-medium">
        👋 你好呀！
      </h3>
      <div className="text-muted-foreground px-4 text-center text-lg">
        选一个技能，一句话就能出成品：🔍 深度研究、📊 做 PPT、📝 智能组卷、📚
        教案生成。下方点一个例子即可开始，内容可自由修改。
      </div>
    </motion.div>
  );
}
