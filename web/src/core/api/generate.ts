// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import {
  FILE_SKILL_CONFIG,
  type FileSkillId,
} from "../skills";

import { authFetch } from "./request";

export interface GeneratedFile {
  blob: Blob;
  filename: string;
}

/** Parse a filename out of a Content-Disposition header (UTF-8 aware). */
function parseFilename(disposition: string | null, fallback: string): string {
  if (!disposition) {
    return fallback;
  }
  const utf8Match = /filename\*=(?:UTF-8''|utf-8'')([^;]+)/i.exec(disposition);
  const plainMatch = /filename="?([^";]+)"?/i.exec(disposition);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  if (plainMatch?.[1]) {
    return plainMatch[1];
  }
  return fallback;
}

/**
 * Call a synchronous file-generating skill endpoint (PPT / exam / lesson).
 * Sends `{ [bodyKey]: text }` with the Bearer token via authFetch, so 401 →
 * login redirect and 402 → renew dialog are handled globally. On success
 * returns the file blob + parsed filename. On other failures (409/429/500/503)
 * authFetch throws an ApiError whose `detail` carries the backend message.
 */
export async function generateSkillFile(
  skill: FileSkillId,
  text: string,
  subSkill?: string,
  attachmentIds?: string[],
): Promise<GeneratedFile> {
  const config = FILE_SKILL_CONFIG[skill];
  const response = await authFetch(config.path, {
    method: "POST",
    body: JSON.stringify({
      [config.bodyKey]: text,
      ...(subSkill ? { sub_skill: subSkill } : {}),
      ...(attachmentIds?.length ? { attachment_ids: attachmentIds } : {}),
    }),
  });
  const blob = await response.blob();
  const filename = parseFilename(
    response.headers.get("Content-Disposition"),
    config.defaultFilename,
  );
  return { blob, filename };
}

/** Trigger a browser download of a blob (mobile-safe: a[download] + object URL). */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
