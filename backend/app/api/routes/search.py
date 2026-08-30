from fastapi import APIRouter, HTTPException

from app.api.schemas import SearchRequest, SearchResponse
from app.rag.retrieval import retrieve

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest):
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    top_k = payload.top_k or 5
    try:
        results = retrieve(payload.query, top_k=top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc

    return {"query": payload.query, "results": results}
