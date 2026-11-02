from pathlib import Path

from subtitle.burn import burn_command, embed_command, escape_filter_path


def test_escape_filter_path_converts_windows_path_and_escapes_colon():
    escaped = escape_filter_path(Path(r"C:\videos\my clip.en.srt"))

    assert escaped.startswith(r"C\:/")
    assert escaped.endswith("/my clip.en.srt")


def test_escape_filter_path_escapes_quotes_and_commas():
    escaped = escape_filter_path(Path("it's, fine.srt"))

    assert r"it\'s\, fine.srt" in escaped


def test_burn_command_uses_requested_encoder():
    nvenc = burn_command(Path("in.mp4"), Path("s.srt"), Path("out.mp4"), "nvenc")
    x264 = burn_command(Path("in.mp4"), Path("s.srt"), Path("out.mp4"), "x264")

    assert nvenc[nvenc.index("-c:v") + 1] == "h264_nvenc"
    assert x264[x264.index("-c:v") + 1] == "libx264"


def test_embed_command_copies_streams_and_adds_text_track():
    command = embed_command(Path("in.mp4"), Path("s.srt"), Path("out.mp4"))

    assert command[command.index("-c") + 1] == "copy"
    assert command[command.index("-c:s") + 1] == "mov_text"
    assert "-vf" not in command
