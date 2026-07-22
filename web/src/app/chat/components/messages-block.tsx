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

import { ConversationStarter } from "./conversation-starter";
import { InputBox } from "./input-box";
import { MessageListView } from "./message-list-view";
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
  const abortControllerRef = useRef<AbortController | null>(null);
  // Prefill payload for the input box; the counter forces a re-fill even when
  // the same example text is clicked twice.
  const [inputPrefill, setInputPrefill] = useState<{
    text: string;
    seq: number;
  } | null>(null);
  const prefillSeq = useRef(0);
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
  const handleFillExample = useCallback((text: string) => {
    prefillSeq.current += 1;
    setInputPrefill({ text, seq: prefillSeq.current });
  }, []);
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
  return (
    <div className={cn("flex h-full flex-col", className)}>
      <MessageListView className="flex flex-grow" onSendMessage={handleSend} />
      {!isReplay ? (
        <div className="relative flex h-42 shrink-0 pb-4">
          {!responding && messageCount === 0 && (
            <ConversationStarter
              className="absolute top-[-238px] left-0"
              onFillExample={handleFillExample}
            />
          )}
          <InputBox
            className="h-full w-full"
            responding={isFileSkill(currentSkill) ? false : responding}
            disabled={isFileSkill(currentSkill) ? responding : false}
            value={inputPrefill?.text}
            key={inputPrefill?.seq}
            onSend={handleSend}
            onCancel={handleCancel}
          />
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
