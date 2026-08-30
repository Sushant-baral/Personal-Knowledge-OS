from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.database.connection import init_db

# Default Vite dev server origins. Add your deployed frontend origin here
# later (or read it from an env var) — this list is intentionally not
# a wildcard, since allow_credentials=True disallows "*" anyway.
FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as exc:
        # Surface a clear message instead of a bare traceback, but don't
        # swallow the failure — a broken DB should stop startup.
        raise RuntimeError(f"Failed to initialize the database: {exc}") from exc
    yield


app = FastAPI(title="Personal Knowledge OS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {"message": "Personal Knowledge OS API"}
