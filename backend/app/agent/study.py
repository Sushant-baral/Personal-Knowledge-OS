"""
Study generation: quiz and flashcard creation for the dedicated
POST /api/study/quiz and POST /api/study/flashcards endpoints.

Same grounding discipline as the rest of the agent: retrieval goes
through the existing app.rag.retrieval.retrieve() (via app/agent/tools.py
— no second retrieval system), generation goes through the existing
app.llm.provider.generate_chat() (no second LLM integration). The only
new thing here is asking the LLM for strict JSON instead of prose, and
safely parsing/validating what comes back, since the current provider
doesn't have a native JSON-mode we can rely on across providers.
"""

import json
import logging
import re
from typing import List, Optional, TypedDict

from sqlalchemy.orm import Session

from app.agent import prompts, tools
from app.llm.provider import generate_chat
from app.llm.settings_store import get_llm_settings

logger = logging.getLogger("app.agent.study")

DEFAULT_COUNT = 10
MIN_COUNT = 1
MAX_COUNT = 20
MIN_TOP_K = 6
MAX_TOP_K = 12


class StudyContentNotFoundError(Exception):
    """Raised when retrieval finds nothing relevant. The route turns this
    into a clear 404 instead of asking the LLM to invent a quiz/flashcards
    from nothing."""


class StudyGenerationError(Exception):
    """Raised when the LLM's output couldn't be parsed into valid
    structured data even after a retry. The route turns this into a
    clear 502 rather than crashing or returning malformed data."""


def generate_quiz(db: Session, query: str, count: Optional[int] = None) -> dict:
    count = _resolve_count(query, count)
    rag_results, source_list = _retrieve_or_raise(query, count)

    context = prompts.format_context(rag_results)
    system_prompt = prompts.quiz_json_system_prompt(count, context)
    questions = _generate_with_retry(
        db=db,
        system_prompt=system_prompt,
        user_note=f"Generate the quiz now for: {query}",
        parser=_parse_quiz_json,
        expected_min=1,
    )

    logger.info("generate_quiz query=%r count_requested=%d count_returned=%d", query, count, len(questions))
    return {"topic": query, "questions": questions, "sources": source_list, "count": len(questions)}


def generate_flashcards(db: Session, query: str, count: Optional[int] = None) -> dict:
    count = _resolve_count(query, count)
    rag_results, source_list = _retrieve_or_raise(query, count)

    context = prompts.format_context(rag_results)
    system_prompt = prompts.flashcard_json_system_prompt(count, context)
    cards = _generate_with_retry(
        db=db,
        system_prompt=system_prompt,
        user_note=f"Generate the flashcards now for: {query}",
        parser=_parse_flashcards_json,
        expected_min=1,
    )

    logger.info("generate_flashcards query=%r count_requested=%d count_returned=%d", query, count, len(cards))
    return {"topic": query, "cards": cards, "sources": source_list, "count": len(cards)}




def _resolve_count(query: str, provided: Optional[int]) -> int:
    if provided is not None:
        return max(MIN_COUNT, min(provided, MAX_COUNT))

    match = re.search(r"\b(\d{1,2})\s*(?:questions?|cards?|flashcards?|mcqs?)\b", query or "", re.I)
    if match:
        n = int(match.group(1))
        if MIN_COUNT <= n <= MAX_COUNT:
            return n

    return DEFAULT_COUNT


def _retrieve_or_raise(query: str, count: int):
    top_k = max(MIN_TOP_K, min(count, MAX_TOP_K))
    result = tools.search_knowledge(query, top_k=top_k)

    if not result["ok"]:
        logger.warning("Study retrieval failed for query=%r: %s", query, result.get("error"))
        raise StudyContentNotFoundError(query)

    rag_results = result["data"]
    if not rag_results:
        raise StudyContentNotFoundError(query)

    seen = set()
    source_list = []
    for r in rag_results:
        page = r["metadata"].get("page")
        key = (r["document"], page)
        if key in seen:
            continue
        seen.add(key)
        source_list.append({"document": r["document"], "page": page})

    return rag_results, source_list


def _generate_with_retry(db: Session, system_prompt: str, user_note: str, parser, expected_min: int) -> list:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_note},
    ]

    saved_settings = get_llm_settings(db) or {}
    llm_kwargs = {
        "provider": saved_settings.get("provider"),
        "api_key": saved_settings.get("api_key"),
        "model": saved_settings.get("model"),
    }

    raw = generate_chat(messages, **llm_kwargs)
    parsed = parser(raw)
    if parsed and len(parsed) >= expected_min:
        return parsed

    logger.warning("Study generation produced invalid/empty JSON on first attempt; retrying once.")

    messages.append({"role": "assistant", "content": raw})
    messages.append(
        {
            "role": "user",
            "content": (
                "That was not valid JSON matching the schema. Reply again with "
                "ONLY the JSON object — nothing else, no code fences."
            ),
        }
    )
    raw_retry = generate_chat(messages, **llm_kwargs)
    parsed_retry = parser(raw_retry)
    if parsed_retry and len(parsed_retry) >= expected_min:
        return parsed_retry

    raise StudyGenerationError("Could not generate valid structured content after a retry.")


def _extract_json_payload(text: str):
    """Strip markdown fences and pull out the first balanced {...} or
    [...] block, then json.loads it. Returns None (never raises) on
    failure so callers can decide how to handle it."""
    if not text:
        return None

    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = cleaned.find(open_ch)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == open_ch:
                depth += 1
            elif cleaned[i] == close_ch:
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break
    return None


class ParsedQuizQuestion(TypedDict):
    question: str
    options: List[str]
    correct_answer: int
    explanation: str


def _parse_quiz_json(text: str) -> List[ParsedQuizQuestion]:
    data = _extract_json_payload(text)
    if data is None:
        return []

    items = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []

    valid: List[ParsedQuizQuestion] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        question = item.get("question")
        options = item.get("options")
        correct_answer = item.get("correct_answer")
        explanation = item.get("explanation", "")

        if not isinstance(question, str) or not question.strip():
            continue
        if not isinstance(options, list) or len(options) < 2:
            continue
        if not all(isinstance(o, str) and o.strip() for o in options):
            continue
        if not isinstance(correct_answer, int) or not (0 <= correct_answer < len(options)):
            continue

        valid.append(
            {
                "question": question.strip(),
                "options": [o.strip() for o in options],
                "correct_answer": correct_answer,
                "explanation": explanation.strip() if isinstance(explanation, str) else "",
            }
        )
    return valid


class ParsedFlashcard(TypedDict):
    front: str
    back: str


def _parse_flashcards_json(text: str) -> List[ParsedFlashcard]:
    data = _extract_json_payload(text)
    if data is None:
        return []

    items = data.get("cards") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []

    valid: List[ParsedFlashcard] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        front = item.get("front")
        back = item.get("back")
        if not isinstance(front, str) or not front.strip():
            continue
        if not isinstance(back, str) or not back.strip():
            continue
        valid.append({"front": front.strip(), "back": back.strip()})
    return valid
