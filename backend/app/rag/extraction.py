"""
Step 1 of the RAG pipeline: get plain text (and, for PDFs, per-page text)
out of an uploaded file's raw bytes.
"""

import io
from typing import List, Optional, Tuple

from pypdf import PdfReader


class UnsupportedFileTypeError(Exception):
    pass


def extract_text(filename: str, raw_bytes: bytes) -> Tuple[str, Optional[List[str]]]:
    """
    Returns (full_text, pages).
    pages is a list of per-page text for PDFs, or None for txt/markdown
    (which have no page concept).
    """
    lower = filename.lower()

    if lower.endswith(".pdf"):
        return _extract_pdf(raw_bytes)

    if lower.endswith(".txt") or lower.endswith(".md") or lower.endswith(".markdown"):
        return _extract_plain_text(raw_bytes), None

    raise UnsupportedFileTypeError(
        f"Unsupported file type for '{filename}'. Supported types: PDF, TXT, Markdown."
    )


def _extract_pdf(raw_bytes: bytes) -> Tuple[str, List[str]]:
    reader = PdfReader(io.BytesIO(raw_bytes))
    pages: List[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    full_text = "\n\n".join(pages)
    return full_text, pages


def _extract_plain_text(raw_bytes: bytes) -> str:
    return raw_bytes.decode("utf-8", errors="replace")
