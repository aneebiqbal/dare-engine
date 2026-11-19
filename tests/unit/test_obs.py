"""The OBS live view: status mapping, snapshot decoding, unreachable state."""
import asyncio
import base64
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))

from app import obs  # noqa: E402

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0test-jpeg").decode()

RESPONSES = {
    "GetVersion": {"obsVersion": "33.0.1", "obsWebSocketVersion": "5.7.6", "rpcVersion": 1},
    "GetStreamStatus": {"outputActive": False},
    "GetRecordStatus": {"outputActive": True, "outputPaused": False},
    "GetCurrentProgramScene": {"sceneName": "Scene"},
    "GetInputList": {"inputs": [{"inputKind": "coreaudio_input_capture", "inputName": "Mic/Aux"}]},
    "GetInputMute": {"inputMuted": False},
    "GetSourceScreenshot": {"imageData": f"data:image/jpeg;base64,{JPEG}"},
}


class FakeResponse:
    requestStatus = types.SimpleNamespace(result=True, code=0, comment=None)

    def __init__(self, data):
        self.responseData = data

    def ok(self):
        return True


class FakeWs:
    fail = False

    def __init__(self, **kwargs):
        pass

    async def connect(self):
        if FakeWs.fail:
            raise OSError("connection refused")

    async def wait_until_identified(self):
        pass

    async def disconnect(self):
        pass

    async def call(self, request):
        return FakeResponse(RESPONSES[request.requestType])


def _install_fake(monkeypatch):
    module = types.ModuleType("simpleobsws")
    module.WebSocketClient = FakeWs
    module.Request = lambda requestType, requestData=None: types.SimpleNamespace(
        requestType=requestType, requestData=requestData
    )
    monkeypatch.setitem(sys.modules, "simpleobsws", module)
    monkeypatch.setattr(obs, "current_user", lambda request: {"id": "u", "role": "admin"})


def test_status_maps_real_state(monkeypatch):
    _install_fake(monkeypatch)
    out = asyncio.run(obs.obs_status(None))
    assert out["connected"] is True
    assert out["obs_version"] == "33.0.1"
    assert out["scene"] == "Scene"
    assert out["recording"] is True
    assert out["audio_inputs"] == [{"name": "Mic/Aux", "muted": False}]


def test_snapshot_decodes_the_data_uri(monkeypatch):
    _install_fake(monkeypatch)
    response = asyncio.run(obs.obs_snapshot(None))
    assert response.media_type == "image/jpeg"
    assert response.body == base64.b64decode(JPEG)


def test_unreachable_obs_is_a_clear_state_not_a_spinner(monkeypatch):
    _install_fake(monkeypatch)
    FakeWs.fail = True
    try:
        out = asyncio.run(obs.obs_status(None))
    finally:
        FakeWs.fail = False
    assert out["connected"] is False
    assert out["how_to_enable"]
