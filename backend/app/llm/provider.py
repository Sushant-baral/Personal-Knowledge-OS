"""
LLM provider abstraction.

Everything about which provider/model/key to use comes from environment
variables — nothing is ever hardcoded. Currently implements "openai" and
"groq"; add another provider by adding a branch in generate_chat() and a
new _generate_<provider>() function, without changing any caller.

generate_chat() is the core entry point: it takes a full list of chat
messages (system prompt + short-term conversation history + the current
user turn), which is what the agent orchestrator needs to support
follow-up questions like "explain it with an example". generate_answer()
is kept as a thin backward-compatible wrapper around it for any caller
that just wants a single-prompt call.
"""

import os
from typing import List, TypedDict


class ChatMessage(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMNotConfiguredError(Exception):
    """Raised when no LLM provider/key is set. Callers should turn this
    into a clear HTTP error instead of letting the server crash."""


class LLMProviderError(Exception):
    """Raised when the configured provider is unsupported or the request
    to it fails."""


def is_llm_configured() -> bool:
    return bool(os.getenv("LLM_PROVIDER")) and bool(os.getenv("LLM_API_KEY"))


def generate_answer(prompt: str) -> str:
    """Backward-compatible single-prompt call. Prefer generate_chat() for
    anything that needs conversation history or a system prompt."""
    return generate_chat([{"role": "user", "content": prompt}])


def generate_chat(messages: List[ChatMessage]) -> str:
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    api_key = os.getenv("LLM_API_KEY")
    model = (os.getenv("LLM_MODEL") or "").strip()

    if not provider or not api_key:
        raise LLMNotConfiguredError(
            "No LLM provider is configured. Set LLM_PROVIDER, LLM_API_KEY, "
            "and LLM_MODEL in backend/.env to enable chat responses."
        )

    if provider == "openai":
        return _generate_openai(messages, api_key=api_key, model=model or "gpt-4o-mini")

    if provider == "groq":
        return _generate_groq(messages, api_key=api_key, model=model or "qwen/qwen3.8-27b")

    raise LLMProviderError(f"Unsupported LLM_PROVIDER '{provider}'.")


def _generate_openai(messages: List[ChatMessage], api_key: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency always listed, defensive only
        raise LLMProviderError("The 'openai' package is not installed.") from exc

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
    except Exception as exc:
        # Never leak the API key or other env values in the error message.
        raise LLMProviderError(f"LLM request failed: {exc}") from exc

    return response.choices[0].message.content or ""


def _generate_groq(messages: List[ChatMessage], api_key: str, model: str) -> str:
    # Groq exposes an OpenAI-compatible API, so we reuse the same client
    # with a different base_url — no new dependency needed.
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
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
