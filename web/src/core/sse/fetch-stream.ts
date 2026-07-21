// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { type StreamEvent } from "./StreamEvent";

export class StreamError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "StreamError";
  }
}

export async function* fetchStream(
  url: string,
  init: RequestInit,
): AsyncIterable<StreamEvent> {
  const { headers: initHeaders, ...restInit } = init;
  const response = await fetch(url, {
    method: "POST",
    ...restInit,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache",
      ...((initHeaders as Record<string, string>) ?? {}),
    },
  });
  if (response.status !== 200) {
    let detail = "";
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body) {
        const d = (body as { detail: unknown }).detail;
        if (typeof d === "string") {
          detail = d;
        }
      }
    } catch {
      // ignore body parse errors
    }
    throw new StreamError(
      response.status,
      detail || `Failed to fetch from ${url}: ${response.status}`,
    );
  }
  // Read from response body, event by event. An event always ends with a '\n\n'.
  const reader = response.body
    ?.pipeThrough(new TextDecoderStream())
    .getReader();
  if (!reader) {
    throw new Error("Response body is not readable");
  }
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += value;
    while (true) {
      const index = buffer.indexOf("\n\n");
      if (index === -1) {
        break;
      }
      const chunk = buffer.slice(0, index);
      buffer = buffer.slice(index + 2);
      const event = parseEvent(chunk);
      if (event) {
        yield event;
      }
    }
  }
}

function parseEvent(chunk: string) {
  let resultEvent = "message";
  let resultData: string | null = null;
  for (const line of chunk.split("\n")) {
    const pos = line.indexOf(": ");
    if (pos === -1) {
      continue;
    }
    const key = line.slice(0, pos);
    const value = line.slice(pos + 2);
    if (key === "event") {
      resultEvent = value;
    } else if (key === "data") {
      resultData = value;
    }
  }
  if (resultEvent === "message" && resultData === null) {
    return undefined;
  }
  return {
    event: resultEvent,
    data: resultData,
  } as StreamEvent;
}
