FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core fontconfig ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY worker/worker_app /app/worker_app
COPY worker/clip /app/clip
COPY shared/llm.py /app/llm_shared.py
COPY shared/key_crypto.py /app/key_crypto.py
COPY shared/platforms.py /app/platforms.py
COPY skills /app/skills
# Optional, GPL-licensed voice-over dependency. Not installed by default.
COPY worker/requirements-voice.txt /app/requirements-voice.txt

EXPOSE 8001
CMD ["uvicorn", "worker_app.main:app", "--host", "0.0.0.0", "--port", "8001"]
