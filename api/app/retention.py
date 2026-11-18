"""Retention: delete raw recordings and preview audio after a set window.

Clips are kept; only the source recording and transient audio are removed.
Runs on startup and on demand through `make cleanup` / `POST /admin/cleanup`.
"""
from __future__ import annotations

import datetime

from . import db, storage
from .config import settings


def sweep() -> dict:
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=settings.recording_retention_days
    )
    deleted_recordings = 0
    deleted_previews = 0

    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT recording_key, "
                "count(*) FILTER (WHERE state <> 'ready') AS not_ready "
                "FROM clips "
                "WHERE recording_key LIKE 'recordings/%%' AND created_at < %s "
                "GROUP BY recording_key",
                (cutoff,),
            )
            recordings = cur.fetchall()

            cur.execute(
                "SELECT v.id, v.audio_key FROM voice_overs v "
                "JOIN clips c ON c.id = v.clip_id "
                "WHERE v.audio_key IS NOT NULL AND c.created_at < %s",
                (cutoff,),
            )
            previews = cur.fetchall()

    store = storage.get_storage()
    for key, not_ready in recordings:
        if not_ready == 0:
            store.delete_prefix(key)
            deleted_recordings += 1
    for voice_over_id, audio_key in previews:
        store.delete_prefix(audio_key)
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM voice_overs WHERE id = %s", (voice_over_id,))
        deleted_previews += 1

    return {"recordings": deleted_recordings, "previews": deleted_previews}
