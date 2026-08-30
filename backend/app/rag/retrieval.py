"""
Step 5 of the RAG pipeline: embed a query and retrieve the most similar
chunks, in the shape the API/agent expects.
"""

from typing import List

from app.rag.embeddings import embed_texts
from app.rag.vector_store import query as vector_query


def retrieve(query_text: str, top_k: int = 5) -> List[dict]:
    query_embedding = embed_texts([query_text])[0]
    raw_matches = vector_query(query_embedding, top_k=top_k)

    results = []
    for match in raw_matches:
        meta = match["metadata"]
        page = meta.get("page")
        results.append(
            {
                "document": meta.get("document_title", "Unknown document"),
                "relevant_text": match["text"],
                "score": round(match["score"], 4),
                "metadata": {
                    "document_id": meta.get("document_id"),
                    "chunk_index": meta.get("chunk_index"),
                    "page": None if page in (None, -1) else page,
                },
            }
        )
    return results
