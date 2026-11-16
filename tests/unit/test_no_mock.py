"""Sprint 4 rule 2: the mock layer is never imported by application code.

Only `web/lib/api.ts` may import it (the sanctioned NEXT_PUBLIC_API_MOCK gate).
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
ALLOWED = {ROOT / "web" / "lib" / "api.ts"}

PATTERN = re.compile(r"""from\s+["'][^"']*lib/mock["']|import\(["'][^"']*mock["']\)""")


def test_mock_is_not_imported_by_pages():
    offenders = []
    for path in (ROOT / "web").rglob("*"):
        if path.suffix not in (".ts", ".tsx"):
            continue
        if "node_modules" in path.parts or ".next" in path.parts:
            continue
        if path == ROOT / "web" / "lib" / "mock.ts":
            continue
        if PATTERN.search(path.read_text()):
            if path not in ALLOWED:
                offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"mock imported outside the sanctioned gate: {offenders}"
