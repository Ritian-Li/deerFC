// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { nanoid } from "nanoid";
import { toast } from "sonner";
import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";

import {
  chatStream,
  generatePodcast,
  generateSkillFile,
  resumeChatStream,
  type ChatEvent,
  type RunReceipt,
} from "../api";
import { ApiError, clearToken, redirectToLogin } from "../api/request";
import type { Message } from "../messages";
import { mergeMessage } from "../messages";
import { FILE_SKILL_CONFIG, type FileSkillId } from "../skills";
import { StreamError } from "../sse";
import { parseJSON } from "../utils";

import { clearAttachments, getReadyAttachmentIds } from "./attachments-store";
import { openRenewDialog, refreshProfile, setRemainingUses } from "./auth-store";
import { getChatStreamSettings, useSettingsStore } from "./settings-store";

const THREAD_ID = nanoid();
const ONGOING_THREAD_KEY = "deerflow.ongoing-thread";

export const useStore = create<{
  responding: boolean;
  threadId: string | undefined;
  messageIds: string[];
  messages: Map<string, Message>;
  researchIds: string[];
  researchPlanIds: Map<string, string>;
  researchReportIds: Map<string, string>;
  researchActivityIds: Map<string, string[]>;
  ongoingResearchId: string | null;
  openResearchId: string | null;
  lastReceipt: RunReceipt | null;
  lastRunError: string | null;

  appendMessage: (message: Message) => void;
  updateMessage: (message: Message) => void;
  updateMessages: (messages: Message[]) => void;
  openResearch: (researchId: string | null) => void;
  closeResearch: () => void;
  setOngoingResearch: (researchId: string | null) => void;
}>((set) => ({
  responding: false,
  threadId: THREAD_ID,
  lastReceipt: null,
  lastRunError: null,
  messageIds: [],
  messages: new Map<string, Message>(),
  researchIds: [],
  researchPlanIds: new Map<string, string>(),
  researchReportIds: new Map<string, string>(),
  researchActivityIds: new Map<string, string[]>(),
  ongoingResearchId: null,
  openResearchId: null,

  appendMessage(message: Message) {
    set((state) => ({
      messageIds: [...state.messageIds, message.id],
      messages: new Map(state.messages).set(message.id, message),
    }));
  },
  updateMessage(message: Message) {
    set((state) => ({
      messages: new Map(state.messages).set(message.id, message),
    }));
  },
  updateMessages(messages: Message[]) {
    set((state) => {
      const newMessages = new Map(state.messages);
      messages.forEach((m) => newMessages.set(m.id, m));
      return { messages: newMessages };
    });
  },
  openResearch(researchId: string | null) {
    set({ openResearchId: researchId });
  },
  closeResearch() {
    set({ openResearchId: null });
  },
  setOngoingResearch(researchId: string | null) {
    set({ ongoingResearchId: researchId });
  },
}));

function getThreadId() {
  return useStore.getState().threadId ?? THREAD_ID;
}

function saveOngoingThread(threadId: string) {
  try {
    localStorage.setItem(ONGOING_THREAD_KEY, threadId);
  } catch {}
}

function clearOngoingThread() {
  try {
    localStorage.removeItem(ONGOING_THREAD_KEY);
  } catch {}
}

export async function sendMessage(
  content?: string,
  {
    interruptFeedback,
  }: {
    interruptFeedback?: string;
  } = {},
  options: { abortSignal?: AbortSignal } = {},
) {
  const threadId = getThreadId();
  if (content != null) {
    appendMessage({
      id: nanoid(),
      threadId,
      role: "user",
      content: content,
      contentChunks: [content],
    });
  }
  useStore.setState({ lastReceipt: null, lastRunError: null });

  // 附件随本次请求消费；请求已发出即清空 chips（后端持有文件，无需重传）
  const attachmentIds = getReadyAttachmentIds();
  if (attachmentIds.length) {
    clearAttachments();
  }

  const settings = getChatStreamSettings();
  const stream = chatStream(
    content ?? "[REPLAY]",
    {
      thread_id: threadId,
      interrupt_feedback: interruptFeedback,
      attachment_ids: attachmentIds.length ? attachmentIds : undefined,
      // The server enforces auto-accepted plans, so the plan-confirmation
      // UI is skipped entirely on the client side as well.
      auto_accepted_plan: true,
      // 联网预调研恒开（设置入口已移除，忽略历史 localStorage 值）
      enable_background_investigation: true,
      // Research sub-skill preset; "general" means no preset (v1 behavior).
      sub_skill: useSettingsStore.getState().currentSubSkill,
      max_plan_iterations: settings.maxPlanIterations,
      max_step_num: settings.maxStepNum,
      max_search_results: settings.maxSearchResults,
      mcp_settings: settings.mcpSettings,
    },
    options,
  );
  if (
    typeof window !== "undefined" &&
    !window.location.search.includes("mock") &&
    !window.location.search.includes("replay=")
  ) {
    // Remember the in-flight thread so we can reconnect after a refresh.
    saveOngoingThread(threadId);
  }
  await consumeStream(stream, { interruptFeedback });
}

/**
 * Send a message for a file-generating skill (PPT / exam / lesson).
 * Does NOT use SSE. Inserts a user message + an assistant "generating…"
 * placeholder card, calls the synchronous endpoint, then swaps the card to a
 * success (download) or error state. Refreshes the quota bar on success.
 * 401/402 are handled globally by authFetch.
 */
export async function sendFileSkillMessage(
  skill: FileSkillId,
  content: string,
  subSkill?: string,
) {
  const threadId = getThreadId();
  const config = FILE_SKILL_CONFIG[skill];

  appendMessage({
    id: nanoid(),
    threadId,
    role: "user",
    content,
    contentChunks: [content],
  });

  const placeholderId = nanoid();
  const attachmentIds = getReadyAttachmentIds();
  if (attachmentIds.length) {
    clearAttachments();
  }
  appendMessage({
    id: placeholderId,
    threadId,
    role: "assistant",
    content: "",
    contentChunks: [],
    isStreaming: true,
    skillResult: {
      skill,
      subSkill,
      status: "loading",
      loadingText: config.loadingText,
      sourceText: content,
      attachmentIds,
    },
  });
  await runFileSkillGeneration(placeholderId, skill, content, subSkill, {
    attachmentIds,
    removeOnAuthError: true,
  });
}

/** Retry a failed file-skill card in place (no new user bubble). */
export async function retryFileSkillMessage(messageId: string) {
  const message = useStore.getState().messages.get(messageId);
  const result = message?.skillResult;
  if (!result || result.status !== "error" || !result.sourceText) {
    return;
  }
  updateSkillMessage(messageId, {
    ...result,
    status: "loading",
    errorText: undefined,
  });
  await runFileSkillGeneration(
    messageId,
    result.skill,
    result.sourceText,
    result.subSkill,
    { attachmentIds: result.attachmentIds },
  );
}

async function runFileSkillGeneration(
  placeholderId: string,
  skill: FileSkillId,
  content: string,
  subSkill: string | undefined,
  options: { attachmentIds?: string[]; removeOnAuthError?: boolean } = {},
) {
  const config = FILE_SKILL_CONFIG[skill];
  const base = {
    skill,
    subSkill,
    loadingText: config.loadingText,
    sourceText: content,
    attachmentIds: options.attachmentIds,
  };
  setResponding(true);
  try {
    const { blob, filename } = await generateSkillFile(
      skill,
      content,
      subSkill,
      options.attachmentIds,
    );
    updateSkillMessage(placeholderId, {
      ...base,
      status: "success",
      filename,
      blob,
    });
    // Success charges 1 use; refresh the quota bar.
    void refreshProfile();
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 402)) {
      // authFetch already redirected / opened the renew dialog. On first send
      // drop the placeholder; on retry keep the card so context isn't lost.
      if (options.removeOnAuthError) {
        removeMessage(placeholderId);
      } else {
        updateSkillMessage(placeholderId, { ...base, status: "error" });
      }
      return;
    }
    const detail =
      error instanceof ApiError && error.detail
        ? error.detail
        : "生成失败，未扣除次数，请重试";
    updateSkillMessage(placeholderId, {
      ...base,
      status: "error",
      errorText: detail,
    });
  } finally {
    setResponding(false);
  }
}

function updateSkillMessage(
  messageId: string,
  skillResult: Message["skillResult"],
) {
  const message = getMessage(messageId);
  if (message) {
    useStore.getState().updateMessage({
      ...message,
      isStreaming: false,
      skillResult,
    });
  }
}

function removeMessage(messageId: string) {
  useStore.setState((state) => {
    const messages = new Map(state.messages);
    messages.delete(messageId);
    return {
      messageIds: state.messageIds.filter((id) => id !== messageId),
      messages,
    };
  });
}

let resuming = false;
/**
 * If a task was still running when the page was refreshed (or the mobile
 * browser was sent to background), reconnect to it and replay all events.
 */
export async function resumeOngoingTask() {
  if (typeof window === "undefined" || resuming) {
    return;
  }
  let threadId: string | null = null;
  try {
    threadId = localStorage.getItem(ONGOING_THREAD_KEY);
  } catch {}
  if (!threadId || useStore.getState().responding) {
    return;
  }
  resuming = true;
  useStore.setState({ threadId });
  try {
    await consumeStream(resumeChatStream(threadId));
  } finally {
    resuming = false;
  }
}

async function consumeStream(
  stream: AsyncIterable<ChatEvent>,
  {
    interruptFeedback,
  }: {
    interruptFeedback?: string;
  } = {},
) {
  setResponding(true);
  let messageId: string | undefined;
  try {
    for await (const event of stream) {
      if (event.type === "run_complete") {
        useStore.setState({
          lastReceipt: event.data.receipt,
          lastRunError: null,
        });
        setRemainingUses(event.data.remaining_uses);
        clearOngoingThread();
        continue;
      }
      if (event.type === "run_error") {
        useStore.setState({ lastRunError: event.data.content });
        setRemainingUses(event.data.remaining_uses);
        clearOngoingThread();
        useStore.getState().setOngoingResearch(null);
        continue;
      }
      const { type, data } = event;
      messageId = data.id;
      let message: Message | undefined;
      if (type === "tool_call_result") {
        message = findMessageByToolCallId(data.tool_call_id);
      } else if (!existsMessage(messageId)) {
        message = {
          id: messageId,
          threadId: data.thread_id,
          agent: data.agent,
          role: data.role,
          content: "",
          contentChunks: [],
          isStreaming: true,
          interruptFeedback,
        };
        appendMessage(message);
      }
      message ??= getMessage(messageId);
      if (message) {
        message = mergeMessage(message, event);
        updateMessage(message);
      }
    }
    clearOngoingThread();
  } catch (error) {
    handleStreamError(error, messageId);
  } finally {
    setResponding(false);
  }
}

function handleStreamError(error: unknown, messageId?: string) {
  const isAborted = (error as Error | undefined)?.name === "AbortError";
  if (isAborted) {
    // User cancelled on purpose; nothing scary to report.
    clearOngoingThread();
  } else if (error instanceof StreamError) {
    if (error.status === 401) {
      clearOngoingThread();
      clearToken();
      redirectToLogin();
      return;
    } else if (error.status === 402) {
      clearOngoingThread();
      openRenewDialog();
      toast("剩余次数不足，输入新卡密即可继续使用");
    } else if (error.status === 404) {
      // Resuming a thread that no longer exists; drop it silently.
      clearOngoingThread();
    } else if (error.status === 409) {
      toast("已有任务正在进行中，请等它完成后再试");
    } else if (error.status === 429) {
      toast("操作有点频繁，请稍等片刻再试");
    } else if (error.status === 503) {
      toast(error.detail || "服务正忙，请稍后再试");
    } else {
      toast(error.detail || "出错了，请稍后重试");
    }
  } else {
    toast("网络开小差了，请检查网络后重试");
  }
  // Finalize any half-streamed message.
  if (messageId != null) {
    const message = getMessage(messageId);
    if (message?.isStreaming) {
      message.isStreaming = false;
      useStore.getState().updateMessage(message);
    }
  }
  useStore.getState().setOngoingResearch(null);
}

function setResponding(value: boolean) {
  useStore.setState({ responding: value });
}

function existsMessage(id: string) {
  return useStore.getState().messageIds.includes(id);
}

function getMessage(id: string) {
  return useStore.getState().messages.get(id);
}

function findMessageByToolCallId(toolCallId: string) {
  return Array.from(useStore.getState().messages.values())
    .reverse()
    .find((message) => {
      if (message.toolCalls) {
        return message.toolCalls.some((toolCall) => toolCall.id === toolCallId);
      }
      return false;
    });
}

function appendMessage(message: Message) {
  if (
    message.agent === "coder" ||
    message.agent === "reporter" ||
    message.agent === "researcher"
  ) {
    if (!getOngoingResearchId()) {
      const id = message.id;
      appendResearch(id);
      openResearch(id);
    }
    appendResearchActivity(message);
  }
  useStore.getState().appendMessage(message);
}

function updateMessage(message: Message) {
  if (
    getOngoingResearchId() &&
    message.agent === "reporter" &&
    !message.isStreaming
  ) {
    useStore.getState().setOngoingResearch(null);
  }
  useStore.getState().updateMessage(message);
}

function getOngoingResearchId() {
  return useStore.getState().ongoingResearchId;
}

function appendResearch(researchId: string) {
  let planMessage: Message | undefined;
  const reversedMessageIds = [...useStore.getState().messageIds].reverse();
  for (const messageId of reversedMessageIds) {
    const message = getMessage(messageId);
    if (message?.agent === "planner") {
      planMessage = message;
      break;
    }
  }
  const messageIds = [researchId];
  messageIds.unshift(planMessage!.id);
  useStore.setState({
    ongoingResearchId: researchId,
    researchIds: [...useStore.getState().researchIds, researchId],
    researchPlanIds: new Map(useStore.getState().researchPlanIds).set(
      researchId,
      planMessage!.id,
    ),
    researchActivityIds: new Map(useStore.getState().researchActivityIds).set(
      researchId,
      messageIds,
    ),
  });
}

function appendResearchActivity(message: Message) {
  const researchId = getOngoingResearchId();
  if (researchId) {
    const researchActivityIds = useStore.getState().researchActivityIds;
    const current = researchActivityIds.get(researchId)!;
    if (!current.includes(message.id)) {
      useStore.setState({
        researchActivityIds: new Map(researchActivityIds).set(researchId, [
          ...current,
          message.id,
        ]),
      });
    }
    if (message.agent === "reporter") {
      useStore.setState({
        researchReportIds: new Map(useStore.getState().researchReportIds).set(
          researchId,
          message.id,
        ),
      });
    }
  }
}

export function openResearch(researchId: string | null) {
  useStore.getState().openResearch(researchId);
}

export function closeResearch() {
  useStore.getState().closeResearch();
}

export async function listenToPodcast(researchId: string) {
  const planMessageId = useStore.getState().researchPlanIds.get(researchId);
  const reportMessageId = useStore.getState().researchReportIds.get(researchId);
  if (planMessageId && reportMessageId) {
    const planMessage = getMessage(planMessageId)!;
    const title = parseJSON(planMessage.content, { title: "Untitled" }).title;
    const reportMessage = getMessage(reportMessageId);
    if (reportMessage?.content) {
      appendMessage({
        id: nanoid(),
        threadId: THREAD_ID,
        role: "user",
        content: "Please generate a podcast for the above research.",
        contentChunks: [],
      });
      const podCastMessageId = nanoid();
      const podcastObject = { title, researchId };
      const podcastMessage: Message = {
        id: podCastMessageId,
        threadId: THREAD_ID,
        role: "assistant",
        agent: "podcast",
        content: JSON.stringify(podcastObject),
        contentChunks: [],
        isStreaming: true,
      };
      appendMessage(podcastMessage);
      // Generating podcast...
      let audioUrl: string | undefined;
      try {
        audioUrl = await generatePodcast(reportMessage.content);
      } catch (e) {
        console.error(e);
        useStore.setState((state) => ({
          messages: new Map(useStore.getState().messages).set(
            podCastMessageId,
            {
              ...state.messages.get(podCastMessageId)!,
              content: JSON.stringify({
                ...podcastObject,
                error: e instanceof Error ? e.message : "Unknown error",
              }),
              isStreaming: false,
            },
          ),
        }));
        toast("An error occurred while generating podcast. Please try again.");
        return;
      }
      useStore.setState((state) => ({
        messages: new Map(useStore.getState().messages).set(podCastMessageId, {
          ...state.messages.get(podCastMessageId)!,
          content: JSON.stringify({ ...podcastObject, audioUrl }),
          isStreaming: false,
        }),
      }));
    }
  }
}

export function useResearchMessage(researchId: string) {
  return useStore(
    useShallow((state) => {
      const messageId = state.researchPlanIds.get(researchId);
      return messageId ? state.messages.get(messageId) : undefined;
    }),
  );
}

export function useMessage(messageId: string | null | undefined) {
  return useStore(
    useShallow((state) =>
      messageId ? state.messages.get(messageId) : undefined,
    ),
  );
}

export function useMessageIds() {
  return useStore(useShallow((state) => state.messageIds));
}

export function useLastInterruptMessage() {
  return useStore(
    useShallow((state) => {
      if (state.messageIds.length >= 2) {
        const lastMessage = state.messages.get(
          state.messageIds[state.messageIds.length - 1]!,
        );
        return lastMessage?.finishReason === "interrupt" ? lastMessage : null;
      }
      return null;
    }),
  );
}

export function useLastFeedbackMessageId() {
  const waitingForFeedbackMessageId = useStore(
    useShallow((state) => {
      if (state.messageIds.length >= 2) {
        const lastMessage = state.messages.get(
          state.messageIds[state.messageIds.length - 1]!,
        );
        if (lastMessage && lastMessage.finishReason === "interrupt") {
          return state.messageIds[state.messageIds.length - 2];
        }
      }
      return null;
    }),
  );
  return waitingForFeedbackMessageId;
}

export function useToolCalls() {
  return useStore(
    useShallow((state) => {
      return state.messageIds
        ?.map((id) => getMessage(id)?.toolCalls)
        .filter((toolCalls) => toolCalls != null)
        .flat();
    }),
  );
}
