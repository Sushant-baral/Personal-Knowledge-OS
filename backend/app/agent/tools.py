"""
Agent tools.

Every tool here is a thin wrapper around functionality that already
exists elsewhere in the codebase (RAG retrieval, the documents table).
No tool talks to Chroma, SQLite, or an LLM provider directly except
through those existing modules — this file adds zero new storage or
retrieval systems, per the requirement to not duplicate what already
works.

Each tool returns a plain dict with a `tool` name, an `ok` flag, and
either `data` or `error`, so the orchestrator can log and handle
failures uniformly without every call site needing its own try/except
shape.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.database.models import Document
from app.rag.retrieval import retrieve

logger = logging.getLogger("app.agent.tools")

RAG_SCORE_THRESHOLD = 0.05
DEFAULT_TOP_K = 4


def search_knowledge(query: str, top_k: int = DEFAULT_TOP_K) -> dict:
    """SEARCH_KNOWLEDGE tool: semantic search over the user's uploaded
    documents via the existing RAG pipeline (app/rag/retrieval.py)."""
    try:
        raw_results = retrieve(query, top_k=top_k)
    except Exception as exc:
        logger.exception("search_knowledge failed for query=%r", query)
        return {"tool": "SEARCH_KNOWLEDGE", "ok": False, "error": str(exc), "data": []}

    results = [r for r in raw_results if r["score"] >= RAG_SCORE_THRESHOLD]
    logger.info(
        "search_knowledge query=%r retrieved=%d kept=%d",
        query,
        len(raw_results),
        len(results),
    )
    return {"tool": "SEARCH_KNOWLEDGE", "ok": True, "data": results}


def get_document(db: Session, document_hint: Optional[str] = None) -> dict:
    """GET_DOCUMENT tool: look up metadata about the user's uploaded
    documents from the existing documents table. If `document_hint`
    matches a title/filename, returns just that document; otherwise
    returns a summary list of everything the user has uploaded."""
    try:
        documents: List[Document] = db.query(Document).order_by(Document.created_at.desc()).all()
    except Exception as exc:
        logger.exception("get_document failed to query documents table")
        return {"tool": "GET_DOCUMENT", "ok": False, "error": str(exc), "data": None}

    if document_hint:
        hint_lower = document_hint.lower()
        match = next(
            (
                d
                for d in documents
                if (d.title and hint_lower in d.title.lower())
                or (d.filename and hint_lower in d.filename.lower())
            ),
            None,
        )
        if match:
            logger.info("get_document matched hint=%r -> document_id=%s", document_hint, match.id)
            return {
                "tool": "GET_DOCUMENT",
                "ok": True,
                "data": {
                    "match_type": "single",
                    "document": _document_summary(match),
                },
            }
        logger.info("get_document hint=%r matched no document", document_hint)
        return {
            "tool": "GET_DOCUMENT",
            "ok": True,
            "data": {"match_type": "not_found", "hint": document_hint, "all_documents": [
                _document_summary(d) for d in documents
            ]},
        }

    logger.info("get_document listing all documents, count=%d", len(documents))
    return {
        "tool": "GET_DOCUMENT",
        "ok": True,
        "data": {"match_type": "list", "all_documents": [_document_summary(d) for d in documents]},
    }


def _document_summary(document: Document) -> dict:
    return {
        "id": document.id,
        "title": document.title or document.filename,
        "filename": document.filename,
        "status": document.status,
        "size_bytes": document.size_bytes,
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }
