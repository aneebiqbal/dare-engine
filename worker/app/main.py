import threading
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import worker

WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The API owns schema creation; the worker retries until the tables exist.
    threading.Thread(target=worker.loop, args=(WORKER_ID,), daemon=True).start()
    yield


app = FastAPI(title="Clipdesk Missions Worker", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "worker": WORKER_ID}
