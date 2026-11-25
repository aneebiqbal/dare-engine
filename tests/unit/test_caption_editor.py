"""Caption editing: the transcript is grouped for the editor, and an edit is a
stored override — never a re-transcription."""
import pathlib
import sys

import pytest
from fastapi import HTTPException

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))

from app.caption_events import group  # noqa: E402


def test_word_style_keeps_each_word():
    words = [{"start": 0.0, "end": 0.4, "text": "a"}, {"start": 0.5, "end": 0.9, "text": "b"}]
    assert group(words, "word") == words


def test_line_style_merges_a_short_phrase():
    words = [{"start": 0.0, "end": 0.4, "text": "a"}, {"start": 0.5, "end": 0.9, "text": "b"}]
    assert group(words, "line") == [{"start": 0.0, "end": 0.9, "text": "a b"}]


def test_line_style_breaks_on_a_long_gap():
    words = [{"start": 0.0, "end": 0.4, "text": "a"}, {"start": 5.0, "end": 5.4, "text": "b"}]
    assert group(words, "line") == words


def test_karaoke_style_groups_like_a_line():
    words = [
        {"start": 0.0, "end": 0.4, "text": "a"},
        {"start": 0.5, "end": 0.9, "text": "b"},
        {"start": 1.0, "end": 1.4, "text": "c"},
        {"start": 1.5, "end": 1.9, "text": "d"},
        {"start": 2.0, "end": 2.4, "text": "e"},
    ]
    assert group(words, "karaoke") == [
        {"start": 0.0, "end": 1.9, "text": "a b c d"},
        {"start": 2.0, "end": 2.4, "text": "e"},
    ]


def test_clean_captions_keeps_valid_rows():
    from app.clips import _clean_captions

    out = _clean_captions([{"start": 1, "end": 2, "text": "hi"}, {"start": 2, "end": 3, "text": " "}])
    assert out == [{"start": 1.0, "end": 2.0, "text": "hi"}]


def test_clean_captions_rejects_bad_rows():
    from app.clips import _clean_captions

    with pytest.raises(HTTPException):
        _clean_captions("nope")
    with pytest.raises(HTTPException):
        _clean_captions([{"start": 3, "end": 2, "text": "backwards"}])
    with pytest.raises(HTTPException):
        _clean_captions([{"start": "x", "end": 2, "text": "bad time"}])
