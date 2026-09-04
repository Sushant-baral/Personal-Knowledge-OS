"""
CRUD for the single-row app_settings table (see app/database/models.py).
This is what lets the LLM provider/key/model be set from the in-app
settings screen instead of requiring a backend/.env file on every
machine the project is run on.

There is always at most one row, with id=1.
"""

from typing import Optional, TypedDict

from sqlalchemy.orm import Session

from app.database.models import AppSettings

SETTINGS_ROW_ID = 1


class LLMSettings(TypedDict):
    provider: Optional[str]
    api_key: Optional[str]
    model: Optional[str]


def get_llm_settings(db: Session) -> Optional[LLMSettings]:
    """Returns the saved settings, or None if nothing has been saved yet
    (in which case callers should fall back to environment variables)."""
    row = db.get(AppSettings, SETTINGS_ROW_ID)
    if row is None:
        return None
    return {"provider": row.llm_provider, "api_key": row.llm_api_key, "model": row.llm_model}


def save_llm_settings(
    db: Session, provider: str, api_key: str, model: Optional[str] = None
) -> AppSettings:
    row = db.get(AppSettings, SETTINGS_ROW_ID)
    if row is None:
        row = AppSettings(id=SETTINGS_ROW_ID)
        db.add(row)

    row.llm_provider = provider.strip().lower()
    row.llm_api_key = api_key.strip()
    row.llm_model = model.strip() if model and model.strip() else None

    db.commit()
    db.refresh(row)
    return row


def clear_llm_settings(db: Session) -> bool:
    """Deletes the saved settings row, if any. After this the app falls
    back to whatever is in backend/.env (if anything)."""
    row = db.get(AppSettings, SETTINGS_ROW_ID)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
