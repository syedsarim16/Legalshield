import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from legalshield_ai.ingest import upsert_statutes

from .config import settings
from .db import FirestoreSession, select
from .errors import install_handlers
from .firebase import admin_ready, firestore_client, public_config
from .models import StatuteSection
from .routers import auth, chat, sections, users

log = logging.getLogger("legalshield")
SAMPLE = Path(__file__).resolve().parent.parent / "legalshield_ai" / "data" / "statutes_sample.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not admin_ready():
        log.warning(
            "Firebase Admin is unavailable; configure a valid service-account JSON via "
            "FIREBASE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS."
        )
    if settings.allow_unreviewed_statutes and admin_ready():
        with FirestoreSession(firestore_client()) as db:
            if not db.scalar(select(StatuteSection)) and SAMPLE.exists():
                result = upsert_statutes(db, json.loads(SAMPLE.read_text(encoding="utf-8"))["records"], allow_unreviewed=True)
                log.warning("Loaded %s SAMPLE statutes (NOT advisor-reviewed). Development only.", result["upserted"])
    yield


app = FastAPI(title="LegalShield API", version="0.1.0", description="Modules 1-3: Auth/RBAC, AI Chatbot, Section Verification", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
install_handlers(app)

API = "/api/v1"
for r in (auth.router, users.router, chat.router, sections.router):
    app.include_router(r, prefix=API)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/firebase/config", include_in_schema=False)
def firebase_config():
    """Return only browser-safe Firebase client settings."""
    config = public_config().copy()
    config["serverEnabled"] = bool(config.get("enabled") and admin_ready())
    return config


# Web UI (frontend/): served by the same server, so no CORS or URL setup is needed.
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/app/")


if FRONTEND.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND, html=True), name="frontend")
