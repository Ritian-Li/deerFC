// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import type { SimpleMCPServerMetadata } from "../mcp";

import { authFetch } from "./request";

export async function queryMCPServerMetadata(config: SimpleMCPServerMetadata) {
  const response = await authFetch("mcp/server/metadata", {
    method: "POST",
    body: JSON.stringify(config),
  });
  return response.json();
}
