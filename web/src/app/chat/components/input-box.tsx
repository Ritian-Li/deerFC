// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, X } from "lucide-react";
import {
  type KeyboardEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { Detective } from "~/components/deer-flow/icons/detective";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { Button } from "~/components/ui/button";
import type { Option } from "~/core/messages";
import { getSkill, SKILLS } from "~/core/skills";
import {
  setCurrentSkill,
  setEnableBackgroundInvestigation,
  useCurrentSkill,
  useSettingsStore,
} from "~/core/store";
import { cn } from "~/lib/utils";

export function InputBox({
  className,
  size,
  responding,
  disabled,
  feedback,
  value,
  onSend,
  onCancel,
  onRemoveFeedback,
}: {
  className?: string;
  size?: "large" | "normal";
  responding?: boolean;
  /** When true, the input and skill switching are locked (e.g. file generation). */
  disabled?: boolean;
  feedback?: { option: Option } | null;
  /** Controlled value used to prefill the box from example clicks. */
  value?: string;
  onSend?: (message: string, options?: { interruptFeedback?: string }) => void;
  onCancel?: () => void;
  onRemoveFeedback?: () => void;
}) {
  const [message, setMessage] = useState("");
  const [imeStatus, setImeStatus] = useState<"active" | "inactive">("inactive");
  const [indent, setIndent] = useState(0);
  const backgroundInvestigation = useSettingsStore(
    (state) => state.general.enableBackgroundInvestigation,
  );
  const currentSkill = useCurrentSkill();
  const skill = getSkill(currentSkill);
  const isResearch = currentSkill === "research";
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);

  // Prefill from example clicks (welcome page / conversation starter).
  useEffect(() => {
    if (value != null) {
      setMessage(value);
      setTimeout(() => textareaRef.current?.focus(), 0);
    }
  }, [value]);

  useEffect(() => {
    if (feedback) {
      setMessage("");

      setTimeout(() => {
        if (feedbackRef.current) {
          setIndent(feedbackRef.current.offsetWidth);
        }
      }, 200);
    }
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 0);
  }, [feedback]);

  const handleSendMessage = useCallback(() => {
    if (responding) {
      onCancel?.();
    } else {
      if (disabled || message.trim() === "") {
        return;
      }
      if (onSend) {
        onSend(message, {
          interruptFeedback: feedback?.option.value,
        });
        setMessage("");
        onRemoveFeedback?.();
      }
    }
  }, [responding, onCancel, disabled, message, onSend, feedback, onRemoveFeedback]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (responding || disabled) {
        return;
      }
      if (
        event.key === "Enter" &&
        !event.shiftKey &&
        !event.metaKey &&
        !event.ctrlKey &&
        imeStatus === "inactive"
      ) {
        event.preventDefault();
        handleSendMessage();
      }
    },
    [responding, disabled, imeStatus, handleSendMessage],
  );

  const locked = Boolean(responding) || Boolean(disabled);

  return (
    <div className="flex w-full flex-col gap-2">
      {/* Skill selector: horizontally scrollable pills, mobile-friendly. */}
      <div className="scrollbar-hide -mx-1 flex items-center gap-2 overflow-x-auto px-1 pb-0.5">
        {SKILLS.map((s) => {
          const active = s.id === currentSkill;
          return (
            <button
              key={s.id}
              type="button"
              disabled={locked}
              onClick={() => {
                if (!locked) {
                  setCurrentSkill(s.id);
                }
              }}
              className={cn(
                "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm whitespace-nowrap transition-colors",
                active
                  ? "border-brand bg-brand/10 text-brand font-medium"
                  : "bg-card text-muted-foreground hover:bg-accent",
                locked && "cursor-not-allowed opacity-60",
              )}
              aria-pressed={active}
            >
              <span>{s.emoji}</span>
              <span>{s.name}</span>
            </button>
          );
        })}
      </div>
      <div className={cn("bg-card relative rounded-[24px] border", className)}>
      <div className="w-full">
        <AnimatePresence>
          {feedback && (
            <motion.div
              ref={feedbackRef}
              className="bg-background border-brand absolute top-0 left-0 mt-3 ml-2 flex items-center justify-center gap-1 rounded-2xl border px-2 py-0.5"
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
            >
              <div className="text-brand flex h-full w-full items-center justify-center text-sm opacity-90">
                {feedback.option.text}
              </div>
              <X
                className="cursor-pointer opacity-60"
                size={16}
                onClick={onRemoveFeedback}
              />
            </motion.div>
          )}
        </AnimatePresence>
        <textarea
          ref={textareaRef}
          disabled={disabled}
          className={cn(
            "m-0 w-full resize-none border-none px-4 py-3 text-lg",
            size === "large" ? "min-h-32" : "min-h-4",
            disabled && "cursor-not-allowed opacity-60",
          )}
          style={{ textIndent: feedback ? `${indent}px` : 0 }}
          placeholder={
            feedback
              ? `Describe how you ${feedback.option.text.toLocaleLowerCase()}?`
              : skill.placeholder
          }
          value={message}
          onCompositionStart={() => setImeStatus("active")}
          onCompositionEnd={() => setImeStatus("inactive")}
          onKeyDown={handleKeyDown}
          onChange={(event) => {
            setMessage(event.target.value);
          }}
        />
      </div>
      <div className="flex items-center px-4 py-2">
        <div className="flex grow">
          {isResearch && (
            <Tooltip
              className="max-w-60"
              title={
                <div>
                  <h3 className="mb-2 font-bold">
                    联网预调研：{backgroundInvestigation ? "开启" : "关闭"}
                  </h3>
                  <p>
                    开启后，助手会在制定研究计划前先做一轮联网搜索，适合涉及时事和新闻的问题。
                  </p>
                </div>
              }
            >
              <Button
                className={cn(
                  "rounded-2xl",
                  backgroundInvestigation && "!border-brand !text-brand",
                )}
                variant="outline"
                size="lg"
                disabled={locked}
                onClick={() =>
                  setEnableBackgroundInvestigation(!backgroundInvestigation)
                }
              >
                <Detective /> 联网预调研
              </Button>
            </Tooltip>
          )}
          {!isResearch && (
            <span className="text-muted-foreground self-center text-xs">
              一句话生成{skill.name}，成品可直接下载
            </span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Tooltip title={responding ? "停止" : "发送"}>
            <Button
              variant="outline"
              size="icon"
              className={cn("h-10 w-10 rounded-full")}
              disabled={disabled && !responding}
              onClick={handleSendMessage}
            >
              {responding ? (
                <div className="flex h-10 w-10 items-center justify-center">
                  <div className="bg-foreground h-4 w-4 rounded-sm opacity-70" />
                </div>
              ) : (
                <ArrowUp />
              )}
            </Button>
          </Tooltip>
        </div>
      </div>
      </div>
    </div>
  );
}
