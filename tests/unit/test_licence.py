"""The default build must not contain GPL/AGPL code."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from licence_check import check_licences  # noqa: E402


def test_no_gpl_in_the_default_build():
    ok, lines = check_licences()
    assert ok, "\n".join(lines)
