import pytest

from subtitle.cli import parse_args


def test_mode_defaults_to_file():
    assert parse_args(["video.mp4"]).mode == ["file"]


def test_mode_accepts_spaces_commas_and_drops_duplicates():
    assert parse_args(["video.mp4", "--mode", "burn", "soft"]).mode == ["burn", "soft"]
    assert parse_args(["video.mp4", "--mode", "burn,soft", "burn"]).mode == ["burn", "soft"]


def test_mode_rejects_unknown_value():
    with pytest.raises(SystemExit):
        parse_args(["video.mp4", "--mode", "both"])
