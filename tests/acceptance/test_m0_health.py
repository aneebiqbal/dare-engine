"""M0 acceptance: `docker compose up` starts every service and all health checks pass.

Run with `make accept`, which brings the stack up first.
"""
import json
import os
import pathlib
import subprocess
import urllib.request

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVICES = ["db", "storage", "api", "worker", "web", "relay"]

API_URL = os.environ.get("CLIPDESK_API_URL", "http://localhost:8000")
WEB_URL = os.environ.get("CLIPDESK_WEB_URL", "http://localhost:3100")
RELAY_URL = os.environ.get("CLIPDESK_RELAY_URL", "http://localhost:19997")


def compose(*args: str) -> str:
    return subprocess.run(
        ["docker", "compose", *args], capture_output=True, text=True, check=True
    ).stdout


def get(url: str):
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.status, json.loads(resp.read())


def test_every_service_is_healthy():
    for service in SERVICES:
        container = compose("ps", "-q", service).strip()
        assert container, f"{service} is not running"
        health = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", container],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert health == "healthy", f"{service} health is {health!r}"


def test_api_ready():
    status, _ = get(f"{API_URL}/healthz/ready")
    assert status == 200


def test_web_health_reports_api_ready():
    status, body = get(f"{WEB_URL}/api/health")
    assert status == 200
    assert body["api"]["status"] == "ready"


def test_relay_control_api_answers():
    status, _ = get(f"{RELAY_URL}/v3/paths/list")
    assert status == 200


def test_openapi_contract_covers_the_spec_endpoints():
    import yaml

    spec = yaml.safe_load((ROOT / "contracts/openapi.yaml").read_text())
    for path in [
        "/healthz",
        "/auth/google/start",
        "/today",
        "/marks",
        "/clips",
        "/missions/{id}/leaderboard",
        "/admin/pool",
        "/admin/questions",
    ]:
        assert path in spec["paths"], f"{path} missing from contracts/openapi.yaml"
    assert spec["components"]["schemas"]["MissionCard"]["$ref"] == "mission-card.schema.json"


def test_served_api_matches_the_implemented_subset():
    status, body = get(f"{API_URL}/openapi.json")
    assert status == 200
    assert "/healthz" in body["paths"]
    assert "/healthz/ready" in body["paths"]
    assert "/today" in body["paths"]


SPEC_EXAMPLE = {
    "id": "m_0214",
    "question": "Can you outrun five stars on a bicycle?",
    "hook_text": "5 STARS. ONE BICYCLE.",
    "setup": "Get five stars downtown, then switch to any bicycle.",
    "win_condition": "Lose the wanted level without leaving the bike.",
    "result_type": "time_seconds",
    "est_minutes": 8,
    "title_options": ["Can you escape 5 stars on a BIKE in GTA 6?"],
    "mode": "free_roam",
    "status": "unverified",
    "evidence": {"askers": 0, "source_video_ids": []},
    "policy": {"spoiler": False, "online_exploit": False},
}


def test_mission_card_schema_accepts_the_spec_example():
    schema = json.loads((ROOT / "contracts/mission-card.schema.json").read_text())
    jsonschema.validate(SPEC_EXAMPLE, schema)


def test_mission_card_schema_rejects_a_bad_card():
    schema = json.loads((ROOT / "contracts/mission-card.schema.json").read_text())
    bad = {**SPEC_EXAMPLE, "result_type": "number_of_horses"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
