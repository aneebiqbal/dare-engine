from contextlib import asynccontextmanager
import datetime

from fastapi import FastAPI

from . import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.migrate()
    yield


app = FastAPI(title="Clipdesk Missions API", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/healthz/ready")
def ready():
    db.check()
    return {"status": "ready"}


@app.get("/today")
def today():
    # M2 fills this from daily_sets.
    return {"date": datetime.date.today().isoformat(), "daily": None, "picks": []}
