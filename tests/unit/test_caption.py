"""Caption styles: the animated karaoke highlight is one event per phrase."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worker"))

from clip.caption import karaoke_text, write_ass  # noqa: E402
from clip.transcribe import Word  # noqa: E402


def test_karaoke_text_uses_each_word_duration():
    text = karaoke_text([Word(0.0, 0.45, "hi"), Word(0.5, 0.75, "there")])
    assert text == "{\\k45}hi {\\k25}there"


def test_karaoke_style_is_one_event_for_the_phrase(tmp_path):
    words = [Word(0.0, 0.4, "one"), Word(0.4, 0.8, "two"), Word(0.8, 1.2, "three")]
    ass = tmp_path / "caption.ass"
    write_ass(str(ass), "HOOK", 2.0, words, [], 0.0, 5.0, caption_style="karaoke")
    text = ass.read_text()
    assert "Style: Karaoke" in text
    assert text.count("Dialogue: 0,0:00:00.00,0:00:01.20,Karaoke") == 1
    assert "\\k" in text
    assert all(word in text for word in ("one", "two", "three"))
