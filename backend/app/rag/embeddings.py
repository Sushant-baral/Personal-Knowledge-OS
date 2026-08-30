"""
Step 3 of the RAG pipeline: turn text into vectors.

By default this uses a small, dependency-free local hashing embedding, so
document upload and search work immediately with no API key and no
network access. If LLM_PROVIDER=openai and LLM_API_KEY are both set, it
uses OpenAI's embedding API instead for meaningfully better semantic
search.

Important: pick one mode and stick with it for a given project — the
vector store's dimensionality is fixed by whichever embedding function
first wrote to it. Switching LLM_PROVIDER after documents are already
indexed means re-uploading them (see the vector store's reset instructions
in the README section of the final response).
"""

import hashlib
import math
import os
from typing import List

LOCAL_EMBEDDING_DIM = 384


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    api_key = os.getenv("LLM_API_KEY")

    if provider == "openai" and api_key:
        return _embed_openai(texts, api_key)

    return [_local_hash_embedding(t) for t in texts]


def _local_hash_embedding(text: str, dim: int = LOCAL_EMBEDDING_DIM) -> List[float]:
    """
    Deterministic, dependency-free "embedding": hashes each token into a
    fixed-size vector (a signed hashing trick). This is lexical, not truly
    semantic, but it's good enough to make search/retrieval genuinely work
    out of the box, and it's trivial to swap out later.
    """
    vector = [0.0] * dim
    tokens = text.lower().split()
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        h = int(digest, 16)
        index = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _embed_openai(texts: List[str], api_key: str) -> List[List[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [item.embedding for item in response.data]
