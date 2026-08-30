import os
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import DocumentOut
from app.database.connection import get_db
from app.database.models import Document
from app.database.seed import get_or_create_default_user
from app.rag.extraction import UnsupportedFileTypeError, extract_text
from app.rag.ingest import ingest_document
from app.rag.vector_store import delete_document_vectors

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}


@router.post("/documents", response_model=DocumentOut, status_code=201)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or "untitled"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext or 'unknown'}'. Supported types: PDF, TXT, Markdown.",
        )

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text, pages = extract_text(filename, raw_bytes)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to read document: {exc}") from exc

    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable text was found in this file.")

    user = get_or_create_default_user(db)
    title = os.path.splitext(filename)[0]

    document = Document(
        user_id=user.id,
        filename=filename,
        title=title,
        file_type=ext.lstrip("."),
        content=text,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        ingest_document(document_id=document.id, title=title, text=text, pages=pages)
    except Exception as exc:
        # Don't keep a document around that has no searchable vectors.
        db.delete(document)
        db.commit()
        raise HTTPException(status_code=422, detail=f"Failed to index document for search: {exc}") from exc

    return document


@router.get("/documents", response_model=List[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    db.delete(document)
    db.commit()
    delete_document_vectors(document_id)
    return None
