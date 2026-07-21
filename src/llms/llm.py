# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI

from src.config import load_yaml_config
from src.config.agents import LLMType

# Per-request model override set by the platform gateway (src/platform/runtime.py).
# The executor task sets this before driving the graph, so every get_llm_by_type()
# call in any node of that run resolves to the user's card-bound model, without
# touching the call sites.
current_model_conf: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "current_model_conf", default=None
)

# Cache for LLM instances, keyed by (model, base_url) or llm_type for conf.yaml ones
_llm_cache: dict[Any, ChatOpenAI] = {}


def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> ChatOpenAI:
    llm_type_map = {
        "reasoning": conf.get("REASONING_MODEL"),
        "basic": conf.get("BASIC_MODEL"),
        "vision": conf.get("VISION_MODEL"),
    }
    llm_conf = llm_type_map.get(llm_type)
    if not llm_conf:
        raise ValueError(f"Unknown LLM type: {llm_type}")
    if not isinstance(llm_conf, dict):
        raise ValueError(f"Invalid LLM Conf: {llm_type}")
    return ChatOpenAI(stream_usage=True, **llm_conf)


def get_llm_by_type(
    llm_type: LLMType,
) -> ChatOpenAI:
    """
    Get LLM instance by type. A per-request platform override (user's card-bound
    model) takes precedence over conf.yaml; falls back to conf.yaml otherwise.
    """
    override = current_model_conf.get()
    if override:
        cache_key = (override["model"], override["base_url"])
        if cache_key in _llm_cache:
            return _llm_cache[cache_key]
        api_key = os.getenv(override.get("api_key_env", ""), "")
        llm = ChatOpenAI(
            model=override["model"],
            base_url=override["base_url"],
            api_key=api_key,
            stream_usage=True,
        )
        _llm_cache[cache_key] = llm
        return llm

    if llm_type in _llm_cache:
        return _llm_cache[llm_type]

    conf = load_yaml_config(
        str((Path(__file__).parent.parent.parent / "conf.yaml").resolve())
    )
    llm = _create_llm_use_conf(llm_type, conf)
    _llm_cache[llm_type] = llm
    return llm


def clear_model_cache_entry(model: str, base_url: str) -> None:
    """Drop a cached instance after admin edits a model entry."""
    _llm_cache.pop((model, base_url), None)
