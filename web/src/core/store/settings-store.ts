// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { create } from "zustand";

import type { MCPServerMetadata, SimpleMCPServerMetadata } from "../mcp";
import {
  DEFAULT_SKILL_ID,
  getDefaultSubSkillId,
  type SkillId,
} from "../skills";

const SETTINGS_KEY = "deerflow.settings";

const DEFAULT_SETTINGS: SettingsState = {
  general: {
    autoAcceptedPlan: false,
    enableBackgroundInvestigation: true,
    maxPlanIterations: 1,
    maxStepNum: 3,
    maxSearchResults: 3,
  },
  /** Currently selected skill in the chat input. */
  currentSkill: DEFAULT_SKILL_ID,
  /** Currently selected sub-skill (scenario preset) of the current skill. */
  currentSubSkill: getDefaultSubSkillId(DEFAULT_SKILL_ID),
  mcp: {
    servers: [],
  },
};

export type SettingsState = {
  general: {
    autoAcceptedPlan: boolean;
    enableBackgroundInvestigation: boolean;
    maxPlanIterations: number;
    maxStepNum: number;
    maxSearchResults: number;
  };
  currentSkill: SkillId;
  currentSubSkill: string;
  mcp: {
    servers: MCPServerMetadata[];
  };
};

export const useSettingsStore = create<SettingsState>(() => ({
  ...DEFAULT_SETTINGS,
}));

export const useSettings = (key: keyof SettingsState) => {
  return useSettingsStore((state) => state[key]);
};

export const changeSettings = (settings: SettingsState) => {
  useSettingsStore.setState(settings);
};

export const loadSettings = () => {
  if (typeof window === "undefined") {
    return;
  }
  const json = localStorage.getItem(SETTINGS_KEY);
  if (json) {
    const settings = JSON.parse(json);
    for (const key in DEFAULT_SETTINGS.general) {
      if (!(key in settings.general)) {
        settings.general[key as keyof SettingsState["general"]] =
          DEFAULT_SETTINGS.general[key as keyof SettingsState["general"]];
      }
    }
    settings.currentSkill ??= DEFAULT_SETTINGS.currentSkill;
    settings.currentSubSkill ??= getDefaultSubSkillId(
      settings.currentSkill as SkillId,
    );

    try {
      useSettingsStore.setState(settings);
    } catch (error) {
      console.error(error);
    }
  }
};

export const saveSettings = () => {
  const latestSettings = useSettingsStore.getState();
  const json = JSON.stringify(latestSettings);
  localStorage.setItem(SETTINGS_KEY, json);
};

export const getChatStreamSettings = () => {
  let mcpSettings:
    | {
        servers: Record<
          string,
          MCPServerMetadata & {
            enabled_tools: string[];
            add_to_agents: string[];
          }
        >;
      }
    | undefined = undefined;
  const { mcp, general } = useSettingsStore.getState();
  const mcpServers = mcp.servers.filter((server) => server.enabled);
  if (mcpServers.length > 0) {
    mcpSettings = {
      servers: mcpServers.reduce((acc, cur) => {
        const { transport, env } = cur;
        let server: SimpleMCPServerMetadata;
        if (transport === "stdio") {
          server = {
            name: cur.name,
            transport,
            env,
            command: cur.command,
            args: cur.args,
          };
        } else {
          server = {
            name: cur.name,
            transport,
            env,
            url: cur.url,
          };
        }
        return {
          ...acc,
          [cur.name]: {
            ...server,
            enabled_tools: cur.tools.map((tool) => tool.name),
            add_to_agents: ["researcher"],
          },
        };
      }, {}),
    };
  }
  return {
    ...general,
    mcpSettings,
  };
};

export function useCurrentSkill() {
  return useSettingsStore((state) => state.currentSkill);
}

export function useCurrentSubSkill() {
  return useSettingsStore((state) => state.currentSubSkill);
}

export function setCurrentSkill(skill: SkillId) {
  // Switching skill resets the sub-skill to that skill's default.
  useSettingsStore.setState({
    currentSkill: skill,
    currentSubSkill: getDefaultSubSkillId(skill),
  });
  saveSettings();
}

export function setCurrentSubSkill(subSkill: string) {
  useSettingsStore.setState({ currentSubSkill: subSkill });
  saveSettings();
}

export function setEnableBackgroundInvestigation(value: boolean) {
  useSettingsStore.setState((state) => ({
    general: {
      ...state.general,
      enableBackgroundInvestigation: value,
    },
  }));
  saveSettings();
}
loadSettings();
