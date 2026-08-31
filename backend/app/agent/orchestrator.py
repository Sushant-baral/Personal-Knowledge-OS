"""
The agent orchestrator.

    User message
          |
          v
    Load short-term history (last few turns of this conversation)
          |
          v
    Planner: decide_action() -> which tool is needed
          |
          v
    Tool execution (search_knowledge / get_document / none)
          |
          v
    Build a system prompt grounded in whatever the tool returned
          |
          v
    Groq (via app.llm.provider.generate_chat), given
    [system prompt, ...short-term history, current user message]
          |
          v
    Save assistant reply, return {answer, sources, conversation_id}

Design notes:
- Tool selection is deterministic (see app/agent/planner.py) — no second
  LLM call is spent on routing, which keeps this fast, free, and easy to
  explain/demo.
- RAG is never a second implementation: SEARCH_KNOWLEDGE and
  STUDY_ASSISTANT both call the *existing* app.rag.retrieval.retrieve()
  through app/agent/tools.py.
- Short-term memory = the last few messages of this conversation, fetched
  from the existing Message table and passed to the LLM as real chat
  history. This is what makes "explain it with an example" resolve "it"
  correctly.
- Long-term memory (user preferences, learning progress, saved concepts)
  is intentionally NOT built out here. The existing lightweight Memory
  table + app/memory/extraction.py keyword-based capture is left in place
  as-is and used only for GENERAL_CHAT context, precisely so it remains a
  clean extension point: swapping in a smarter long-term memory system
  later only means changing memory/extraction.py + memory/store.py, not
  this file.
- Tool failures never crash the request: a failed tool logs the error and
  the agent continues with empty context rather than 500ing.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.agent import prompts, tools
from app.agent.planner import decide_action
from app.database.models import Conversation, Document, Message
from app.database.seed import get_or_create_default_user
from app.llm.provider import generate_chat
from app.memory.extraction import maybe_extract_memory
from app.memory.store import retrieve_memories, store_memory

logger = logging.getLogger("app.agent.orchestrator")

SHORT_TERM_HISTORY_TURNS = 8  

STUDY_ASSISTANT_TOP_K = 6


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


def _load_short_term_history(db: Session, conversation_id: int, limit: int) -> List[dict]:
    """Fetch the last `limit` messages of this conversation, oldest first,
    in the {role, content} shape the LLM provider expects. Called BEFORE
    the current user message is saved, so it never duplicates it."""
    recent = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    recent.reverse()
    return [{"role": m.role, "content": m.content} for m in recent]


def _looks_personal(message: str) -> bool:
    """Very small heuristic, kept from the original single-path agent:
    decides whether it's worth pulling in long-term Memory rows for
    general conversation. Not used by the retrieval-grounded tools, since
    those are already grounded in the user's documents."""
    lowered = message.lower()
    return any(
        phrase in lowered
        for phrase in ("what do you know about me", "remind me", "what was i", "what have i")
    )


def handle_chat(db: Session, message: str, conversation_id: Optional[int] = None) -> dict:
    user = get_or_create_default_user(db)
    conversation = _get_or_create_conversation(db, user_id=user.id, conversation_id=conversation_id)

    history = _load_short_term_history(db, conversation.id, SHORT_TERM_HISTORY_TURNS)

    db.add(Message(conversation_id=conversation.id, role="user", content=message))
    db.commit()

    try:
        memory_candidate = maybe_extract_memory(message)
        if memory_candidate:
            store_memory(
                db,
                user_id=user.id,
                content=memory_candidate["content"],
                memory_type=memory_candidate["memory_type"],
            )
    except Exception:
        logger.exception("Long-term memory extraction failed; continuing without it.")

    known_titles = _known_document_titles(db)

    decision = decide_action(message, known_document_titles=known_titles)
    logger.info(
        "decision tool=%s reason=%r study_mode=%s document_hint=%r",
        decision.tool,
        decision.reason,
        decision.study_mode,
        decision.document_hint,
    )

    rag_results: List[dict] = []
    system_prompt: str

    if decision.tool == "GENERAL_CHAT":
        system_prompt = prompts.general_chat_system_prompt()
        if _looks_personal(message):
            memories = retrieve_memories(db, user_id=user.id, limit=5)
            if memories:
                memory_lines = "\n".join(f"- {m.content}" for m in memories)
                system_prompt += f"\n\nThings you've previously noted about this user:\n{memory_lines}"

    elif decision.tool == "SEARCH_KNOWLEDGE":
        result = tools.search_knowledge(message)
        rag_results = result["data"] if result["ok"] else []
        if not result["ok"]:
            logger.warning("SEARCH_KNOWLEDGE tool failed: %s", result.get("error"))
        system_prompt = prompts.search_knowledge_system_prompt(prompts.format_context(rag_results))

    elif decision.tool == "STUDY_ASSISTANT":
        result = tools.search_knowledge(message, top_k=STUDY_ASSISTANT_TOP_K)
        rag_results = result["data"] if result["ok"] else []
        if not result["ok"]:
            logger.warning("STUDY_ASSISTANT retrieval failed: %s", result.get("error"))
        system_prompt = prompts.study_assistant_system_prompt(
            decision.study_mode or "explain", prompts.format_context(rag_results)
        )

    elif decision.tool == "GET_DOCUMENT":
        result = tools.get_document(db, decision.document_hint)
        if result["ok"]:
            system_prompt = prompts.get_document_system_prompt(result["data"])
        else:
            logger.warning("GET_DOCUMENT tool failed: %s", result.get("error"))
            system_prompt = (
                f"{prompts.BASE_IDENTITY} The user asked about their uploaded documents, "
                "but looking that up failed internally. Apologize briefly and suggest "
                "they try again."
            )

    else:  

        logger.error("Unknown tool from planner: %s", decision.tool)
        system_prompt = prompts.general_chat_system_prompt()

    llm_messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": message}]

    answer = generate_chat(llm_messages)
    logger.info("response generated tool=%s answer_length=%d", decision.tool, len(answer))

    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()

    sources = [
        {"document": r["document"], "page": r["metadata"]["page"], "relevance": r["score"]}
        for r in rag_results
    ]

    return {
        "answer": answer,
        "sources": sources,
        "conversation_id": conversation.id,
        "tool_used": decision.tool,
    }


def _known_document_titles(db: Session) -> List[str]:
    rows = db.query(Document.title, Document.filename).all()
    return [title or filename for title, filename in rows]
