"""
Step 2 of the RAG pipeline: split extracted text into overlapping chunks
suitable for embedding + retrieval. Chunking is character-based (simple,
predictable, no extra NLP dependency).
"""

from typing import List, Optional, TypedDict


class Chunk(TypedDict):
    text: str
    index: int
    page: Optional[int]


DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 100


def chunk_text(
    text: str,
    pages: Optional[List[str]] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> List[Chunk]:
    if pages:
        return _chunk_by_pages(pages, chunk_size, overlap)
    return _chunk_flat(text, chunk_size, overlap, page=None)


def _chunk_flat(text: str, chunk_size: int, overlap: int, page: Optional[int]) -> List[Chunk]:
    chunks: List[Chunk] = []
    length = len(text)
    step = max(chunk_size - overlap, 1)
    start = 0
    index = 0
    while start < length:
        end = min(start + chunk_size, length)
        piece = text[start:end].strip()
        if piece:
            chunks.append({"text": piece, "index": index, "page": page})
            index += 1
        start += step
    return chunks


def _chunk_by_pages(pages: List[str], chunk_size: int, overlap: int) -> List[Chunk]:
    chunks: List[Chunk] = []
    index = 0
    for page_number, page_text in enumerate(pages, start=1):
        for c in _chunk_flat(page_text, chunk_size, overlap, page=page_number):
            chunks.append({"text": c["text"], "index": index, "page": page_number})
            index += 1
    return chunks
