// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";
import { FastForward, Play } from "lucide-react";
import { useCallback, useRef, useState } from "react";

import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { fastForwardReplay } from "~/core/api";
import { useReplayMetadata } from "~/core/api/hooks";
import { useReplay } from "~/core/replay";
import { isFileSkill } from "~/core/skills";
import {
  sendFileSkillMessage,
  sendMessage,
  useCurrentSkill,
  useCurrentSubSkill,
  useMessageIds,
  useStore,
} from "~/core/store";
import { cn } from "~/lib/utils";

import { InputBox } from "./input-box";
import { MessageListView } from "./message-list-view";
import { TemplateGallery } from "./template-gallery";
import { Welcome } from "./welcome";

export function MessagesBlock({ className }: { className?: string }) {
  const messageIds = useMessageIds();
  const messageCount = messageIds.length;
  const responding = useStore((state) => state.responding);
  const { isReplay } = useReplay();
  const { title: replayTitle, hasError: replayHasError } = useReplayMetadata();
  const [replayStarted, setReplayStarted] = useState(false);
  const currentSkill = useCurrentSkill();
  const currentSubSkill = useCurrentSubSkill();
  // 模板卡点击后预填输入框的提示词（InputBox 的受控 value 通道）。
  const [templatePrompt, setTemplatePrompt] = useState<string | undefined>();
  const abortControllerRef = useRef<AbortController | null>(null);
  const handleSend = useCallback(
    async (message: string, options?: { interruptFeedback?: string }) => {
      if (isFileSkill(currentSkill)) {
        // File-generating skill: synchronous endpoint, no SSE.
        await sendFileSkillMessage(currentSkill, message, currentSubSkill);
        return;
      }
      const abortController = new AbortController();
      abortControllerRef.current = abortController;
      try {
        await sendMessage(
          message,
          {
            interruptFeedback: options?.interruptFeedback,
          },
          {
            abortSignal: abortController.signal,
          },
        );
      } catch {}
    },
    [currentSkill, currentSubSkill],
  );
  const handleCancel = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
  }, []);
  const handleStartReplay = useCallback(() => {
    setReplayStarted(true);
    void sendMessage();
  }, [setReplayStarted]);
  const [fastForwarding, setFastForwarding] = useState(false);
  const handleFastForwardReplay = useCallback(() => {
    setFastForwarding(!fastForwarding);
    fastForwardReplay(!fastForwarding);
  }, [fastForwarding]);
  const isLauncher = messageCount === 0 && !responding && !isReplay;
  return (
    <div
      className={cn(
        "flex h-full flex-col",
        // 启动台状态：无消息列表，选择区垂直居中
        isLauncher && "justify-center",
        className,
      )}
    >
      {!isLauncher && (
        <MessageListView
          className="flex flex-grow"
          onSendMessage={handleSend}
        />
      )}
      {!isReplay ? (
        <div className="relative flex h-fit min-h-42 shrink-0 flex-col gap-6 pb-4">
          {/* 空会话 = 启动台：极简标语 + 大号子能力缩略图；开始对话后消失 */}
          {isLauncher && (
            <div className="flex flex-col items-center gap-1 pt-2">
              <h2 className="text-2xl font-medium">一句话，出成品</h2>
              <p className="text-muted-foreground text-sm">
                选一个能力，说出需求，直接拿到可下载的成果
              </p>
            </div>
          )}
          <InputBox
            className="h-full w-full"
            responding={isFileSkill(currentSkill) ? false : responding}
            disabled={isFileSkill(currentSkill) ? responding : false}
            hero={isLauncher}
            value={templatePrompt}
            onSend={handleSend}
            onCancel={handleCancel}
          />
          {/* 模板灵感库：仅启动台展示，会话开始后让位给消息流 */}
          {isLauncher && (
            <TemplateGallery onPickTemplate={setTemplatePrompt} />
          )}
        </div>
      ) : (
        <>
          <div
            className={cn(
              "fixed bottom-[calc(50vh+80px)] left-0 transition-all duration-500 ease-out",
              replayStarted && "pointer-events-none scale-150 opacity-0",
            )}
          >
            <Welcome />
          </div>
          <motion.div
            className="mb-4 h-fit w-full items-center justify-center"
            initial={{ opacity: 0, y: "20vh" }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Card
              className={cn(
                "w-full transition-all duration-300",
                !replayStarted && "translate-y-[-40vh]",
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex-grow">
                  <CardHeader>
                    <CardTitle>
                      <RainbowText animated={responding}>
                        {responding ? "回放中" : `${replayTitle}`}
                      </RainbowText>
                    </CardTitle>
                    <CardDescription>
                      <RainbowText animated={responding}>
                        {responding
                          ? "正在回放对话…"
                          : replayStarted
                            ? "回放已停止。"
                            : `你正处于回放模式，点击右侧"播放"开始。`}
                      </RainbowText>
                    </CardDescription>
                  </CardHeader>
                </div>
                {!replayHasError && (
                  <div className="pr-4">
                    {responding && (
                      <Button
                        className={cn(fastForwarding && "animate-pulse")}
                        variant={fastForwarding ? "default" : "outline"}
                        onClick={handleFastForwardReplay}
                      >
                        <FastForward size={16} />
                        快进
                      </Button>
                    )}
                    {!replayStarted && (
                      <Button className="w-24" onClick={handleStartReplay}>
                        <Play size={16} />
                        播放
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </Card>
          </motion.div>
        </>
      )}
    </div>
  );
}
