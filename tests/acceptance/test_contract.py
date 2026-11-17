"""The contract and the implemented routes must match, in both directions."""
import json
import pathlib
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _methods(spec: dict) -> set[tuple[str, str]]:
    found = set()
    for path, operations in spec.get("paths", {}).items():
        for method in operations:
            if method.lower() in ("get", "post", "put", "patch", "delete", "head", "options"):
                found.add((method.upper(), path))
    return found


def test_contract_covers_every_implemented_route():
    with urllib.request.urlopen("http://localhost:8000/openapi.json", timeout=10) as resp:
        served = json.load(resp)
    contract = yaml.safe_load((ROOT / "contracts/openapi.yaml").read_text())

    served_methods = _methods(served)
    contract_methods = _methods(contract)

    missing = served_methods - contract_methods
    extra = contract_methods - served_methods
    assert not missing, f"routes missing from the contract: {sorted(missing)}"
    assert not extra, f"contract entries with no route: {sorted(extra)}"


def test_contract_keeps_the_mission_card_schema():
    contract = yaml.safe_load((ROOT / "contracts/openapi.yaml").read_text())
    ref = contract["components"]["schemas"]["MissionCard"]["$ref"]
    assert ref == "mission-card.schema.json"
