// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { nanoid } from "nanoid";
import { create } from "zustand";

import { uploadAttachment } from "../api/attachments";

/** Max attachments per request; mirrors the backend MAX_ATTACHMENTS. */
export const MAX_ATTACHMENTS = 5;

export interface AttachmentItem {
  /** Client-side key, stable across upload lifecycle. */
  localId: string;
  /** Server id, present once the upload succeeds. */
  id?: string;
  name: string;
  kind: "image" | "document";
  chars?: number;
  status: "uploading" | "ready" | "error";
  /** Friendly error (upload failure or backend parse failure). */
  error?: string;
  /** Object URL for image thumbnails; revoked on remove/clear. */
  previewUrl?: string;
}

export const useAttachmentsStore = create<{ items: AttachmentItem[] }>(() => ({
  items: [],
}));

const IMAGE_TYPES = /^image\/(png|jpe?g|webp|gif)$/;

function isImage(file: File) {
  return IMAGE_TYPES.test(file.type);
}

/**
 * Add files (from the picker or a paste event) and upload them concurrently.
 * Files beyond the per-request cap are dropped with an error chip so the
 * user sees why they didn't attach.
 */
export function addAttachmentFiles(files: File[]) {
  const existing = useAttachmentsStore.getState().items.length;
  for (const [index, file] of files.entries()) {
    const localId = nanoid();
    const overflow = existing + index >= MAX_ATTACHMENTS;
    const item: AttachmentItem = {
      localId,
      name: file.name || (isImage(file) ? "粘贴的图片.png" : "附件"),
      kind: isImage(file) ? "image" : "document",
      status: overflow ? "error" : "uploading",
      error: overflow ? `最多 ${MAX_ATTACHMENTS} 个附件` : undefined,
      previewUrl: isImage(file) ? URL.createObjectURL(file) : undefined,
    };
    useAttachmentsStore.setState((state) => ({ items: [...state.items, item] }));
    if (overflow) {
      continue;
    }
    void uploadAttachment(file)
      .then((meta) => {
        patchAttachment(localId, {
          id: meta.id,
          status: meta.error ? "error" : "ready",
          chars: meta.chars,
          error: meta.error || undefined,
        });
      })
      .catch((error: Error) => {
        patchAttachment(localId, {
          status: "error",
          error: error.message || "上传失败，请重试",
        });
      });
  }
}

function patchAttachment(localId: string, patch: Partial<AttachmentItem>) {
  useAttachmentsStore.setState((state) => ({
    items: state.items.map((item) =>
      item.localId === localId ? { ...item, ...patch } : item,
    ),
  }));
}

export function removeAttachment(localId: string) {
  useAttachmentsStore.setState((state) => {
    const item = state.items.find((i) => i.localId === localId);
    if (item?.previewUrl) {
      URL.revokeObjectURL(item.previewUrl);
    }
    return { items: state.items.filter((i) => i.localId !== localId) };
  });
}

export function clearAttachments() {
  for (const item of useAttachmentsStore.getState().items) {
    if (item.previewUrl) {
      URL.revokeObjectURL(item.previewUrl);
    }
  }
  useAttachmentsStore.setState({ items: [] });
}

export function useAttachments() {
  return useAttachmentsStore((state) => state.items);
}

/** Server ids of successfully parsed attachments, ready to send. */
export function getReadyAttachmentIds(): string[] {
  return useAttachmentsStore
    .getState()
    .items.filter((i) => i.status === "ready" && i.id)
    .map((i) => i.id!);
}

/** True when any successfully uploaded image attachment is present. */
export function hasReadyImageAttachment(): boolean {
  return useAttachmentsStore
    .getState()
    .items.some((i) => i.kind === "image" && i.status === "ready");
}
