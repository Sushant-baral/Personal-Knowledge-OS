"""
LLM provider abstraction.

Which provider/model/key to use can come from two places, checked in
this order:
1. Explicit overrides passed in by the caller (provider/api_key/model
   args below) — these come from the app_settings DB row that the
   in-app Settings screen writes to (see app/llm/settings_store.py).
2. Environment variables (LLM_PROVIDER / LLM_API_KEY / LLM_MODEL) from
   backend/.env, used only when no override is passed in — this keeps
   the original .env-based setup working for anyone who still wants it.

Currently implements "openai" and "groq"; add another provider by
adding a branch in generate_chat() and a new _generate_<provider>()
function, without changing any caller.

generate_chat() is the core entry point: it takes a full list of chat
messages (system prompt + short-term conversation history + the current
user turn), which is what the agent orchestrator needs to support
follow-up questions like "explain it with an example". generate_answer()
is kept as a thin backward-compatible wrapper around it for any caller
that just wants a single-prompt call.
"""

import os
from typing import List, Optional, TypedDict


class ChatMessage(TypedDict):
    role: str  

    content: str


class LLMNotConfiguredError(Exception):
    """Raised when no LLM provider/key is set. Callers should turn this
    into a clear HTTP error instead of letting the server crash."""


class LLMProviderError(Exception):
    """Raised when the configured provider is unsupported or the request
    to it fails."""


def is_llm_configured(provider: Optional[str] = None, api_key: Optional[str] = None) -> bool:
    provider = provider or os.getenv("LLM_PROVIDER")
    api_key = api_key or os.getenv("LLM_API_KEY")
    return bool(provider) and bool(api_key)


def generate_answer(prompt: str) -> str:
    """Backward-compatible single-prompt call. Prefer generate_chat() for
    anything that needs conversation history or a system prompt."""
    return generate_chat([{"role": "user", "content": prompt}])


def generate_chat(
    messages: List[ChatMessage],
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    provider = (provider or os.getenv("LLM_PROVIDER") or "").strip().lower()
    api_key = api_key or os.getenv("LLM_API_KEY")
    model = (model or os.getenv("LLM_MODEL") or "").strip()

    if not provider or not api_key:
        raise LLMNotConfiguredError(
            "No LLM provider is configured. Set it up from the app's "
            "Settings screen, or set LLM_PROVIDER, LLM_API_KEY, and "
            "LLM_MODEL in backend/.env, to enable chat responses."
        )

    if provider == "openai":
        return _generate_openai(messages, api_key=api_key, model=model or "gpt-4o-mini")

    if provider == "groq":
        return _generate_groq(messages, api_key=api_key, model=model or "qwen/qwen3.8-27b")

    raise LLMProviderError(f"Unsupported LLM provider '{provider}'.")


def _generate_openai(messages: List[ChatMessage], api_key: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:  

        raise LLMProviderError("The 'openai' package is not installed.") from exc

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
    except Exception as exc:
        raise LLMProviderError(f"LLM request failed: {exc}") from exc

    return response.choices[0].message.content or ""


def _generate_groq(messages: List[ChatMessage], api_key: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:  

        raise LLMProviderError("The 'openai' package is not installed.") from exc

    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
    except Exception as exc:
        raise LLMProviderError(f"LLM request failed: {exc}") from exc

    return response.choices[0].message.content or ""
