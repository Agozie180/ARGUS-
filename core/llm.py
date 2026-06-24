"""LLM provider routing for Argus — Qwen-first, OpenAI optional fallback.

Argus's reasoning and reflection narration are powered by **Qwen** by default
(Alibaba's open model family, via DashScope), aligning with the Bitget AI
hackathon stack. OpenAI is supported only as an optional fallback when explicitly
configured. Either way the call is optional: if no provider is reachable the
callers degrade gracefully to deterministic rule-based logic, so Argus never
fabricates confidence or invents reasoning it didn't actually run.

Configuration (all via env, all optional):
    ARGUS_LLM_PROVIDER   "qwen" (default) | "openai" | "none"
    ARGUS_QWEN_MODEL     default "dashscope/qwen-plus"
    ARGUS_OPENAI_MODEL   default "gpt-4o-mini"
    DASHSCOPE_API_KEY    Qwen credential (DashScope)
    OPENAI_API_KEY       OpenAI credential (fallback only)
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

try:  # litellm gives one interface across Qwen (DashScope) and OpenAI.
    import litellm  # type: ignore
    litellm_available = True
except ImportError:  # pragma: no cover - optional dependency
    litellm_available = False


def primary_provider() -> str:
    return os.getenv("ARGUS_LLM_PROVIDER", "qwen").strip().lower()


def qwen_model() -> str:
    return os.getenv("ARGUS_QWEN_MODEL", "dashscope/qwen-plus")


def openai_model() -> str:
    return os.getenv("ARGUS_OPENAI_MODEL", "gpt-4o-mini")


def provider_label() -> str:
    """Human-readable label for the active reasoning provider (for UI/docs)."""
    p = primary_provider()
    if p == "qwen":
        return "Qwen"
    if p == "openai":
        return "OpenAI"
    return "Rule-based (no LLM)"


def _model_chain() -> List[str]:
    """Ordered list of models to try: configured primary first, then fallback."""
    p = primary_provider()
    if p == "none":
        return []
    if p == "openai":
        chain = [openai_model()]
        if os.getenv("DASHSCOPE_API_KEY"):
            chain.append(qwen_model())
        return chain
    # Qwen-first (default). OpenAI only joins the chain if a key is present.
    chain = [qwen_model()]
    if os.getenv("OPENAI_API_KEY"):
        chain.append(openai_model())
    return chain


def _has_any_key() -> bool:
    return bool(os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY"))


def chat(messages: List[dict], json_mode: bool = True, temperature: float = 0.2) -> Optional[str]:
    """Synchronous completion. Returns content string, or None to signal the
    caller to use its deterministic fallback (no LLM reachable/configured)."""
    if not litellm_available or not _has_any_key():
        return None
    kwargs = {"messages": messages, "temperature": temperature}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    for model in _model_chain():
        try:
            resp = litellm.completion(model=model, **kwargs)
            return resp.choices[0].message.content
        except Exception as e:  # try the next provider in the chain
            logger.warning("LLM provider '%s' failed: %s", model, e)
            continue
    return None


async def achat(messages: List[dict], json_mode: bool = True, temperature: float = 0.2) -> Optional[str]:
    """Async variant of :func:`chat`."""
    if not litellm_available or not _has_any_key():
        return None
    kwargs = {"messages": messages, "temperature": temperature}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    for model in _model_chain():
        try:
            resp = await litellm.acompletion(model=model, **kwargs)
            return resp.choices[0].message.content
        except Exception as e:
            logger.warning("LLM provider '%s' failed: %s", model, e)
            continue
    return None
