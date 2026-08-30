"""
Development logging setup.

Called once at app startup (see app/main.py). Every agent module logs
through logging.getLogger("app.agent") (or a sub-logger of it), so all
agent activity shows up with a consistent "app.agent.*" prefix in the
uvicorn console — useful for a live demo: you can watch, for each
message, the chosen tool, the tool input, how many chunks came back,
and when the final LLM response was generated.

Never log secrets: nothing here ever touches LLM_API_KEY or other env
values — only the user's message text and derived agent decisions.
"""

import logging
import os


def configure_logging() -> None:
    level_name = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Quiet down noisy third-party loggers so agent logs stand out.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
