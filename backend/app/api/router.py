from fastapi import APIRouter

from app.api.routes import chat, documents, health, search

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(chat.router, tags=["chat"])
