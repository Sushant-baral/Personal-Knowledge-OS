"""
The planning step of the agent: decide which tool a user message needs,
*before* anything is retrieved or sent to Groq.

This is deliberately a small, deterministic, keyword/regex-based
classifier — not a second LLM call. That keeps the agent fast, free,
predictable, and easy to explain/demo in a college project ("here is the
exact rule that routed this message"). It mirrors the same style already
used in app/memory/extraction.py for memory-worthiness detection.

Tools (see app/agent/tools.py for what each one actually does):

  GENERAL_CHAT      Small talk / greetings — no document retrieval.
  GET_DOCUMENT      Questions *about* the user's document collection
                     itself (what's uploaded, status of a file, etc.)
                     rather than about the content inside them.
  STUDY_ASSISTANT   Summaries, explanations, flashcards, quizzes —
                     study-oriented requests. Still grounded in
                     retrieved knowledge; it just shapes the answer
                     differently than a plain Q&A.
  SEARCH_KNOWLEDGE  The default for anything that looks like a factual
                     question about the user's knowledge base.

Priority matters: GENERAL_CHAT is checked first (so "hi" never triggers
a pointless vector search), then GET_DOCUMENT, then STUDY_ASSISTANT,
and SEARCH_KNOWLEDGE is the fallback.
"""

import re
from dataclasses import dataclass, field
from typing import Literal, Optional

ToolName = Literal["GENERAL_CHAT", "GET_DOCUMENT", "STUDY_ASSISTANT", "SEARCH_KNOWLEDGE"]

StudyMode = Literal["summary", "quiz", "flashcards", "explain"]


@dataclass
class AgentDecision:
    tool: ToolName
    reason: str
    study_mode: Optional[StudyMode] = None
    document_hint: Optional[str] = None
    params: dict = field(default_factory=dict)


_GREETING_PATTERN = re.compile(
    r"^\s*(hi|hello|hey|yo|hola|good\s?(morning|afternoon|evening)|"
    r"how are you|what'?s up|thanks|thank you|bye|goodbye)\b",
    re.I,
)

_GET_DOCUMENT_PATTERN = re.compile(
    r"\b(what|which|how many)\b.*\bdocuments?\b"
    r"|\blist\s+(?:my|the|all)?\s*documents?\b"
    r"|\bdocuments?\s+(?:have i|did i)\s+upload"
    r"|\btell me about (?:the|my|this) document\b"
    r"|\bdocument\s+(?:status|info|information)\b"
    r"|\bwhat'?s in (?:the|my) document\b",
    re.I,
)

_QUOTED_NAME_PATTERN = re.compile(r"[\"“']([^\"”']{2,80})[\"”']")

_SUMMARY_PATTERN = re.compile(r"\bsummar(y|ize|ise|ies)\b", re.I)

_QUIZ_STANDALONE_PATTERN = re.compile(
    r"\bquiz(?:zes)?\b"  

    r"|\bmcqs?\b"  

    r"|\bmultiple[\s-]choice\b"  

    r"|\btest(?:ing)?\s+(?:me\b|my\s+(?:knowledge|understanding)\b)"  

    r"|\bpractice\s+questions\b"  

    r"|\bquestion\s+bank\b",
    re.I,
)
_QUESTION_WORD_PATTERN = re.compile(r"\b(?:questions?|qns?)\b", re.I)
_QUIZ_INTENT_VERB_PATTERN = re.compile(
    r"\b(?:ask|make|give|create|generate|write|prepare|test|quiz)\b", re.I
)


def _looks_like_quiz_request(text: str) -> bool:
    if _QUIZ_STANDALONE_PATTERN.search(text):
        return True
    return bool(_QUESTION_WORD_PATTERN.search(text) and _QUIZ_INTENT_VERB_PATTERN.search(text))


_FLASHCARD_PATTERN = re.compile(r"\bflash\s?cards?\b", re.I)
_EXPLAIN_PATTERN = re.compile(
    r"\bexplain\b|\blike i'?m a beginner\b|\bin simple terms\b|\bteach me\b|\bin layman'?s? terms\b",
    re.I,
)


def decide_action(message: str, known_document_titles: Optional[list] = None) -> AgentDecision:
    """
    Pick a tool for this message. `known_document_titles` (optional) lets
    GET_DOCUMENT match a specific uploaded document by name so the tool
    can look it up directly instead of guessing.
    """
    text = message.strip()
    known_document_titles = known_document_titles or []

    if not text:
        return AgentDecision(tool="GENERAL_CHAT", reason="Empty message.")

    word_count = len(text.split())

    if _GREETING_PATTERN.search(text) and word_count <= 6:
        return AgentDecision(tool="GENERAL_CHAT", reason="Matched greeting/small-talk pattern.")

    if _GET_DOCUMENT_PATTERN.search(text):
        document_hint = _extract_document_hint(text, known_document_titles)
        return AgentDecision(
            tool="GET_DOCUMENT",
            reason="Message asks about the user's uploaded documents, not their content.",
            document_hint=document_hint,
        )

    if _looks_like_quiz_request(text):
        return AgentDecision(tool="STUDY_ASSISTANT", reason="Quiz/question-generation request.", study_mode="quiz")
    if _FLASHCARD_PATTERN.search(text):
        return AgentDecision(tool="STUDY_ASSISTANT", reason="Flashcard request.", study_mode="flashcards")
    if _SUMMARY_PATTERN.search(text):
        return AgentDecision(tool="STUDY_ASSISTANT", reason="Summary request.", study_mode="summary")
    if _EXPLAIN_PATTERN.search(text):
        return AgentDecision(tool="STUDY_ASSISTANT", reason="Explanation request.", study_mode="explain")

    return AgentDecision(tool="SEARCH_KNOWLEDGE", reason="Default: treated as a factual knowledge-base question.")


def _extract_document_hint(text: str, known_document_titles: list) -> Optional[str]:
    """Best-effort: a quoted title, or a substring match against titles
    the user has actually uploaded. Returns None if nothing matches —
    the GET_DOCUMENT tool then falls back to listing all documents."""
    quoted = _QUOTED_NAME_PATTERN.search(text)
    if quoted:
        return quoted.group(1).strip()

    lowered = text.lower()
    for title in known_document_titles:
        if title and title.lower() in lowered:
            return title
    return None
