// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useEffect, useMemo } from "react";

import { resumeOngoingTask, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

import { MessagesBlock } from "./components/messages-block";
import { ResearchBlock } from "./components/research-block";

export default function Main() {
  const openResearchId = useStore((state) => state.openResearchId);
  const doubleColumnMode = useMemo(
    () => openResearchId !== null,
    [openResearchId],
  );

  // Reconnect to an in-flight task after a refresh or when the mobile
  // browser comes back from background.
  useEffect(() => {
    void resumeOngoingTask();
    const handleVisible = () => {
      if (document.visibilityState === "visible") {
        void resumeOngoingTask();
      }
    };
    document.addEventListener("visibilitychange", handleVisible);
    return () => {
      document.removeEventListener("visibilitychange", handleVisible);
    };
  }, []);

  return (
    <div
      className={cn(
        "flex h-full w-full justify-center-safe px-2 pt-12 pb-2 sm:px-4 sm:pb-4",
        doubleColumnMode && "lg:gap-8",
      )}
    >
      <MessagesBlock
        className={cn(
          "w-full shrink-0 transition-all duration-300 ease-out lg:max-w-[768px]",
          !doubleColumnMode &&
            `lg:w-[768px] lg:translate-x-[min(max(calc((100vw-538px)*0.75),575px)/2,960px/2)]`,
          doubleColumnMode && `hidden lg:flex lg:w-[538px] lg:max-w-[538px]`,
        )}
      />
      <ResearchBlock
        className={cn(
          "pb-4 transition-all duration-300 ease-out",
          !doubleColumnMode &&
            "hidden lg:block lg:w-[min(max(calc((100vw-538px)*0.75),575px),960px)] lg:scale-0",
          doubleColumnMode &&
            "w-full lg:w-[min(max(calc((100vw-538px)*0.75),575px),960px)]",
        )}
        researchId={openResearchId}
      />
    </div>
  );
}
