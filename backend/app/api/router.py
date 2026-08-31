from fastapi import APIRouter

from app.api.routes import chat, documents, health, search, study

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(study.router, tags=["study"])
