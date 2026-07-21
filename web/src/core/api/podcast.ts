// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { authFetch } from "./request";

export async function generatePodcast(content: string) {
  const response = await authFetch("podcast/generate", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
  const arrayBuffer = await response.arrayBuffer();
  const blob = new Blob([arrayBuffer], { type: "audio/mp3" });
  const audioUrl = URL.createObjectURL(blob);
  return audioUrl;
}
