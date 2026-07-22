// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

export type MessageRole = "user" | "assistant" | "tool";

/**
 * State of a file-generating skill (PPT / exam / lesson) rendered as a
 * dedicated "deliverable card" in the message list. Kept in-memory only:
 * the blob is not serialized anywhere.
 */
export interface SkillResult {
  /** File skill that produced this message. */
  skill: "ppt" | "exam" | "lesson";
  status: "loading" | "success" | "error";
  /** Loading copy shown while generating. */
  loadingText: string;
  /** Deliverable filename (from Content-Disposition or default). */
  filename?: string;
  /** In-memory generated file, ready to download. */
  blob?: Blob;
  /** Friendly error message (backend detail) when status === "error". */
  errorText?: string;
}

export interface Message {
  id: string;
  threadId: string;
  agent?:
    | "coordinator"
    | "planner"
    | "researcher"
    | "coder"
    | "reporter"
    | "podcast";
  role: MessageRole;
  isStreaming?: boolean;
  content: string;
  contentChunks: string[];
  toolCalls?: ToolCallRuntime[];
  options?: Option[];
  finishReason?: "stop" | "interrupt" | "tool_calls";
  interruptFeedback?: string;
  /** Present on assistant messages produced by a file-generating skill. */
  skillResult?: SkillResult;
}

export interface Option {
  text: string;
  value: string;
}

export interface ToolCallRuntime {
  id: string;
  name: string;
  args: Record<string, unknown>;
  argsChunks?: string[];
  result?: string;
}
