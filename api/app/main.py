from contextlib import asynccontextmanager
import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .missions import router as missions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.migrate()
    yield


app = FastAPI(title="Clipdesk Missions API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(missions_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/healthz/ready")
def ready():
    db.check()
    return {"status": "ready"}
