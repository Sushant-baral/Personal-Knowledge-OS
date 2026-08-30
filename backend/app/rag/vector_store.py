"""
Step 4 of the RAG pipeline: store and search chunk vectors.

Uses a local, on-disk ChromaDB collection — no server to run, and the
data survives restarts (stored under backend/chroma_data/). Every chunk
keeps document_id, document_title, chunk_index, and page as metadata, so
this module is the only thing that would need to change if the vector
backend is later swapped for PostgreSQL + pgvector — nothing in
retrieval.py, embeddings.py, or the API routes would need to change.
"""

import os
from typing import List, Optional, TypedDict

import chromadb

_CHROMA_PATH = os.getenv(
    "CHROMA_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_data"),
)
_COLLECTION_NAME = "pkos_chunks"

_client = None
_collection = None


class VectorMatch(TypedDict):
    text: str
    metadata: dict
    score: float


def _get_collection():
    global _client, _collection
    if _collection is None:
        os.makedirs(_CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=os.path.abspath(_CHROMA_PATH))
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(document_id: int, document_title: str, chunks: list, embeddings: List[List[float]]) -> None:
    if not chunks:
        return

    collection = _get_collection()
    ids = [f"doc{document_id}-chunk{c['index']}" for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "document_title": document_title,
            "chunk_index": c["index"],
            # Chroma metadata can't store None, so use -1 as "no page".
            "page": c["page"] if c["page"] is not None else -1,
        }
        for c in chunks
    ]
    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def query(query_embedding: List[float], top_k: int = 5) -> List[VectorMatch]:
    collection = _get_collection()
    if collection.count() == 0:
        return []

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
    )

    documents = result.get("documents") or [[]]
    metadatas = result.get("metadatas") or [[]]
    distances = result.get("distances") or [[]]

    matches: List[VectorMatch] = []
    for doc_text, meta, distance in zip(documents[0], metadatas[0], distances[0]):
        score = max(0.0, 1.0 - distance)
        matches.append({"text": doc_text, "metadata": dict(meta), "score": score})
    return matches


def delete_document_vectors(document_id: int) -> None:
    collection = _get_collection()
    collection.delete(where={"document_id": document_id})
