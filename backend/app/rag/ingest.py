"""
Ties chunking, embedding, and vector storage together for a single
document. Called once, right after a document is saved to the SQL
database.
"""

from typing import List, Optional

from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_texts
from app.rag.vector_store import add_chunks


def ingest_document(document_id: int, title: str, text: str, pages: Optional[List[str]] = None) -> int:
    """Returns the number of chunks that were indexed."""
    chunks = chunk_text(text, pages=pages)
    if not chunks:
        return 0

    embeddings = embed_texts([c["text"] for c in chunks])
    add_chunks(document_id=document_id, document_title=title, chunks=chunks, embeddings=embeddings)
    return len(chunks)
