import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import db, storage
from .account import router as account_router
from .admin import router as admin_router
from .ai import router as ai_router
from .auth import router as auth_router
from .calendar import router as calendar_router
from .clips import router as clips_router
from .community import router as community_router
from .config import settings
from .games import router as games_router
from .hooks import router as hooks_router
from .longform import router as longform_router
from .missions import router as missions_router
from .models import router as models_router
from .obs import router as obs_router
from .provider import router as provider_router
from .ssd import router as ssd_router
from .studio import router as studio_router
from .tours import router as tours_router
from .users import csrf_protect


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.dev_auth_enabled and settings.app_env == "production":
        raise RuntimeError("DEV_AUTH_ENABLED must never be set in production")
    db.migrate()
    storage.ensure_bucket()
    try:
        from .retention import sweep

        sweep()
    except Exception:
        pass  # retention must never block startup
    if settings.research_enabled:
        from .research import start_scheduler

        start_scheduler()
    yield


app = FastAPI(title="Clipdesk Missions API", version="0.6.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("WEB_ORIGIN", "http://localhost:3100")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    # Consistent shape, with `detail` kept for older clients.
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error": {"status": exc.status_code, "message": exc.detail}},
    )


for router in (
    auth_router,
    calendar_router,
    longform_router,
    missions_router,
    models_router,
    clips_router,
    community_router,
    account_router,
    admin_router,
    ai_router,
    games_router,
    obs_router,
    provider_router,
    ssd_router,
    studio_router,
    tours_router,
):
    app.include_router(router, dependencies=[Depends(csrf_protect)])
app.include_router(hooks_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/healthz/ready")
def ready():
    db.check()
    return {"status": "ready"}
