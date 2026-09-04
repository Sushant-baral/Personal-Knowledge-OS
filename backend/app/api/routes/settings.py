import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import SettingsResponse, SettingsUpdateRequest
from app.database.connection import get_db
from app.llm.settings_store import clear_llm_settings, get_llm_settings, save_llm_settings

router = APIRouter()

SUPPORTED_PROVIDERS = {"groq", "openai"}


@router.get("/settings", response_model=SettingsResponse)
def read_settings(db: Session = Depends(get_db)):
    saved = get_llm_settings(db)
    if saved and saved.get("provider") and saved.get("api_key"):
        return SettingsResponse(
            is_configured=True,
            source="database",
            provider=saved["provider"],
            model=saved.get("model"),
            api_key_hint=_hint(saved["api_key"]),
        )

    env_provider = os.getenv("LLM_PROVIDER")
    env_api_key = os.getenv("LLM_API_KEY")
    if env_provider and env_api_key:
        return SettingsResponse(
            is_configured=True,
            source="environment",
            provider=env_provider,
            model=os.getenv("LLM_MODEL"),
            api_key_hint=_hint(env_api_key),
        )

    return SettingsResponse(is_configured=False, source="none")


@router.put("/settings", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdateRequest, db: Session = Depends(get_db)):
    provider = payload.provider.strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider '{payload.provider}'. Use one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}.",
        )
    if not payload.api_key or not payload.api_key.strip():
        raise HTTPException(status_code=400, detail="API key must not be empty.")

    row = save_llm_settings(db, provider=provider, api_key=payload.api_key, model=payload.model)

    return SettingsResponse(
        is_configured=True,
        source="database",
        provider=row.llm_provider,
        model=row.llm_model,
        api_key_hint=_hint(row.llm_api_key),
    )


@router.delete("/settings")
def delete_settings(db: Session = Depends(get_db)):
    clear_llm_settings(db)
    return {"ok": True}


def _hint(api_key: str) -> str:
    tail = api_key[-4:] if len(api_key) >= 4 else api_key
    return f"••••{tail}"
