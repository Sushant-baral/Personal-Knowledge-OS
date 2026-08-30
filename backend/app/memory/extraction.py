"""
Deterministic (no LLM call) check for whether an incoming chat message
contains something worth remembering long-term. Intentionally simple —
this is NOT a classifier, just a small set of keyword patterns — so it
stays fast, free, and easy to reason about. Expand the pattern list as
you learn what's worth keeping.
"""

import re
from typing import Optional, TypedDict

_PATTERNS = [
    (re.compile(r"\bremember that\b", re.I), "explicit"),
    (re.compile(r"\bi(?:'m| am) (?:currently )?(?:studying|learning)\b", re.I), "activity"),
    (re.compile(r"\bi(?:'m| am) working on\b", re.I), "activity"),
    (re.compile(r"\bi prefer\b", re.I), "preference"),
    (re.compile(r"\bmy (?:project|goal|plan) is\b", re.I), "goal"),
]


class MemoryCandidate(TypedDict):
    content: str
    memory_type: str


def maybe_extract_memory(message: str) -> Optional[MemoryCandidate]:
    stripped = message.strip()
    if not stripped:
        return None

    for pattern, memory_type in _PATTERNS:
        if pattern.search(stripped):
            return {"content": stripped, "memory_type": memory_type}

    return None
