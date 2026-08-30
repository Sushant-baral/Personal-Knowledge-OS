"""
The agent: a deterministic orchestration layer, not an autonomous
framework. For every message it:

  1. Always attempts RAG retrieval against the user's documents, but only
     keeps results above a minimum similarity score — so an irrelevant
     question doesn't drag in noise.
  2. Only pulls in long-term memory when the question *looks* personal
     (keyword-based check — see _looks_personal below).
  3. Builds one prompt combining whatever context it found (possibly
     none) and sends it to the LLM.
  4. Saves the conversation, and separately checks whether the user's
     message itself is worth remembering going forward.

This keeps the decision process simple, deterministic, and easy to
follow end-to-end.
"""

import re
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import Conversation, Message
from app.database.seed import get_or_create_default_user
from app.llm.provider import generate_answer
from app.memory.extraction import maybe_extract_memory
from app.memory.store import retrieve_memories, store_memory
from app.rag.retrieval import retrieve

RAG_SCORE_THRESHOLD = 0.05
RAG_TOP_K = 3
MEMORY_LIMIT = 5

_PERSONAL_PATTERN = re.compile(
    r"\bwhat (?:was|am|have) i\b"
    r"|\bwhat do you know about me\b"
    r"|\bremind me\b"
    r"|\b(?:i|my)\b.*\b(?:studying|working on|prefer|recently|preference)\b",
    re.I,
)


def _looks_personal(message: str) -> bool:
    return bool(_PERSONAL_PATTERN.search(message))


def _get_or_create_conversation(db: Session, user_id: int, conversation_id: Optional[int]) -> Conversation:
    if conversation_id is not None:
        conversation = db.get(Conversation, conversation_id)
        if conversation is not None and conversation.user_id == user_id:
            return conversation

    conversation = Conversation(user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _build_prompt(message: str, rag_results: list, memories: list) -> str:
    context_blocks = []

    if rag_results:
        knowledge_lines = "\n".join(
            f"- ({r['document']}): {r['relevant_text']}" for r in rag_results
        )
        context_blocks.append(f"Relevant knowledge from the user's documents:\n{knowledge_lines}")

    if memories:
        memory_lines = "\n".join(f"- {m.content}" for m in memories)
        context_blocks.append(f"What you know about the user:\n{memory_lines}")

    if not context_blocks:
        return f"User question: {message}"

    context = "\n\n".join(context_blocks)
    return (
        "You are the assistant inside a Personal Knowledge OS. Answer the "
        "user's question directly and concisely. Ground your answer in the "
        "context below when it's relevant; otherwise answer from general "
        "knowledge.\n\n"
        f"{context}\n\nUser question: {message}"
    )


def handle_chat(db: Session, message: str, conversation_id: Optional[int] = None) -> dict:
    user = get_or_create_default_user(db)
    conversation = _get_or_create_conversation(db, user_id=user.id, conversation_id=conversation_id)

    db.add(Message(conversation_id=conversation.id, role="user", content=message))
    db.commit()

    # Decide whether this message itself is worth remembering. Done before
    # calling the LLM so memory storage still works even when no LLM
    # provider is configured yet.
    memory_candidate = maybe_extract_memory(message)
    if memory_candidate:
        store_memory(
            db,
            user_id=user.id,
            content=memory_candidate["content"],
            memory_type=memory_candidate["memory_type"],
        )

    # 1. RAG — always attempted, only kept if actually relevant.
    rag_results = retrieve(message, top_k=RAG_TOP_K)
    rag_results = [r for r in rag_results if r["score"] >= RAG_SCORE_THRESHOLD]

    # 2. Memory — only pulled in for questions that look personal.
    memories = retrieve_memories(db, user_id=user.id, limit=MEMORY_LIMIT) if _looks_personal(message) else []

    # 3. Ask the LLM (raises LLMNotConfiguredError / LLMProviderError,
    #    which the route turns into a clean HTTP error). The user message
    #    and any extracted memory are already saved by this point.
    prompt = _build_prompt(message, rag_results, memories)
    answer = generate_answer(prompt)

    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()

    sources = [
        {"document": r["document"], "page": r["metadata"]["page"], "relevance": r["score"]}
        for r in rag_results
    ]

    return {"answer": answer, "sources": sources, "conversation_id": conversation.id}
