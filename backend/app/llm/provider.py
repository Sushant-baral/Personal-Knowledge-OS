"""
LLM provider abstraction.

Everything about which provider/model/key to use comes from environment
variables — nothing is ever hardcoded. Currently implements "openai";
add another provider by adding a branch in generate_answer() and a new
_generate_<provider>() function, without changing any caller.
"""

import os


class LLMNotConfiguredError(Exception):
    """Raised when no LLM provider/key is set. Callers should turn this
    into a clear HTTP error instead of letting the server crash."""


class LLMProviderError(Exception):
    """Raised when the configured provider is unsupported or the request
    to it fails."""


def is_llm_configured() -> bool:
    return bool(os.getenv("LLM_PROVIDER")) and bool(os.getenv("LLM_API_KEY"))


def generate_answer(prompt: str) -> str:
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    api_key = os.getenv("LLM_API_KEY")
    model = (os.getenv("LLM_MODEL") or "").strip()

    if not provider or not api_key:
        raise LLMNotConfiguredError(
            "No LLM provider is configured. Set LLM_PROVIDER, LLM_API_KEY, "
            "and LLM_MODEL in backend/.env to enable chat responses."
        )

    if provider == "openai":
        return _generate_openai(prompt, api_key=api_key, model=model or "gpt-4o-mini")

    raise LLMProviderError(f"Unsupported LLM_PROVIDER '{provider}'.")


def _generate_openai(prompt: str, api_key: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency always listed, defensive only
        raise LLMProviderError("The 'openai' package is not installed.") from exc

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        # Never leak the API key or other env values in the error message.
        raise LLMProviderError(f"LLM request failed: {exc}") from exc

    return response.choices[0].message.content or ""
