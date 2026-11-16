import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .auth import router as auth_router
from .config import settings
from .missions import router as missions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.dev_auth_enabled and settings.app_env == "production":
        raise RuntimeError("DEV_AUTH_ENABLED must never be set in production")
    db.migrate()
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


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/healthz/ready")
def ready():
    db.check()
    return {"status": "ready"}
