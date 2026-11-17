"""Generate contracts/openapi.yaml from the implemented routes.

The mission card shape is owned by contracts/mission-card.schema.json, so it is
injected as a schema reference after generation.
"""
from __future__ import annotations

import pathlib

import yaml

from .main import app

OUT = pathlib.Path(__file__).resolve().parents[1] / "contracts" / "openapi.yaml"


def main() -> None:
    spec = app.openapi()
    schemas = spec.setdefault("components", {}).setdefault("schemas", {})
    schemas["MissionCard"] = {"$ref": "mission-card.schema.json"}
    OUT.write_text(yaml.safe_dump(spec, sort_keys=False))
    print(f"wrote {OUT} ({len(spec['paths'])} paths)")


if __name__ == "__main__":
    main()
