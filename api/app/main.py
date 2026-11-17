import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db, storage
from .account import router as account_router
from .admin import router as admin_router
from .auth import router as auth_router
from .clips import router as clips_router
from .community import router as community_router
from .config import settings
from .hooks import router as hooks_router
from .missions import router as missions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.dev_auth_enabled and settings.app_env == "production":
        raise RuntimeError("DEV_AUTH_ENABLED must never be set in production")
    db.migrate()
    storage.ensure_bucket()
    yield


app = FastAPI(title="Clipdesk Missions API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("WEB_ORIGIN", "http://localhost:3100")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(missions_router)
app.include_router(clips_router)
app.include_router(community_router)
app.include_router(account_router)
app.include_router(admin_router)
app.include_router(hooks_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/healthz/ready")
def ready():
    db.check()
    return {"status": "ready"}
