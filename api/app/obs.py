"""OBS WebSocket status and snapshot for the Go-Live page.

OBS 31+ ships obs-websocket 5.x. The page shows the real connection, stream,
record and scene state, plus a periodic scene snapshot (a still, not a video
feed — the page says so). If OBS is off or the WebSocket server is disabled the
endpoint returns a clear state and how to enable it, never a spinner.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Request
from fastapi.responses import Response

from .config import settings
from .users import current_user

router = APIRouter()

HOW_TO_ENABLE = (
    "Start OBS, open Tools → WebSocket Server Settings, enable the WebSocket "
    "server, set a password, then put it in OBS_WS_PASSWORD in .env."
)


async def _connect():
    import simpleobsws

    ws = simpleobsws.WebSocketClient(
        url=settings.obs_ws_url, password=settings.obs_ws_password
    )
    await ws.connect()
    await ws.wait_until_identified()
    return ws


async def _call(ws, name: str, data: dict | None = None):
    import simpleobsws

    resp = await ws.call(simpleobsws.Request(name, data or {}))
    if not resp.ok():
        raise RuntimeError(f"{name} failed: {resp.requestStatus.comment or resp.requestStatus.code}")
    return resp.responseData or {}


async def _close(ws) -> None:
    try:
        await ws.disconnect()
    except Exception:
        pass


@router.get("/live/obs")
async def obs_status(request: Request):
    current_user(request)
    if not settings.obs_ws_url:
        return {"enabled": False, "reason": "OBS_WS_URL is not set", "how_to_enable": HOW_TO_ENABLE}
    try:
        ws = await _connect()
    except Exception as exc:
        return {
            "enabled": True,
            "connected": False,
            "error": type(exc).__name__,
            "detail": str(exc)[:200],
            "how_to_enable": HOW_TO_ENABLE,
        }
    audio = []
    try:
        version = await _call(ws, "GetVersion")
        stream = await _call(ws, "GetStreamStatus")
        record = await _call(ws, "GetRecordStatus")
        scene = await _call(ws, "GetCurrentProgramScene")
        inputs = await _call(ws, "GetInputList")
        for item in inputs.get("inputs") or []:
            if "audio" not in str(item.get("inputKind", "")).lower():
                continue
            name = item.get("inputName")
            try:
                muted = await _call(ws, "GetInputMute", {"inputName": name})
            except Exception:
                muted = {}
            audio.append({"name": name, "muted": bool(muted.get("inputMuted"))})
            if len(audio) >= 4:
                break
    except Exception as exc:
        return {"enabled": True, "connected": True, "error": str(exc)[:200]}
    finally:
        await _close(ws)

    return {
        "enabled": True,
        "connected": True,
        "obs_version": version.get("obsVersion"),
        "websocket_version": version.get("obsWebSocketVersion"),
        "rpc_version": version.get("rpcVersion"),
        "streaming": bool(stream.get("outputActive")),
        "recording": bool(record.get("outputActive")),
        "record_paused": bool(record.get("outputPaused")),
        "scene": scene.get("sceneName"),
        "audio_inputs": audio,
        "how_to_enable": HOW_TO_ENABLE,
    }


@router.get("/live/obs/snapshot")
async def obs_snapshot(request: Request):
    """A periodic still of the program scene. Not a live video feed."""
    current_user(request)
    if not settings.obs_ws_url:
        return Response(status_code=404, content="OBS not configured")
    try:
        ws = await _connect()
    except Exception:
        return Response(status_code=503, content="OBS not reachable")
    try:
        scene = await _call(ws, "GetCurrentProgramScene")
        shot = await _call(
            ws,
            "GetSourceScreenshot",
            {
                "sourceName": scene.get("sceneName"),
                "imageFormat": "jpeg",
                "imageWidth": settings.obs_snapshot_width,
                "imageCompressionQuality": 70,
            },
        )
        data = shot.get("imageData", "")
        if "," in data:
            data = data.split(",", 1)[1]
        return Response(content=base64.b64decode(data), media_type="image/jpeg")
    except Exception as exc:
        return Response(
            status_code=502,
            content=f"snapshot failed: {type(exc).__name__}",
            media_type="text/plain",
        )
    finally:
        await _close(ws)
