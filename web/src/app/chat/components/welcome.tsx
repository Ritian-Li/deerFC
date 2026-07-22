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
        欢迎使用{" "}
        <a
          href="https://github.com/bytedance/deer-flow"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
        >
          AI 深度研究助手
        </a>
        ，一个基于前沿大语言模型的深度研究助手，帮你联网检索、整理信息、完成复杂任务。
      </div>
    </motion.div>
  );
}
