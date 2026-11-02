from collections.abc import Sequence
from pathlib import Path

from subtitle.transcribe import Segment


def format_timestamp(seconds: float) -> str:
    """Format seconds as an SRT timestamp, e.g. 3661.5 -> '01:01:01,500'."""
    total_ms = round(seconds * 1000)
    hours, total_ms = divmod(total_ms, 3_600_000)
    minutes, total_ms = divmod(total_ms, 60_000)
    secs, millis = divmod(total_ms, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def to_srt(segments: Sequence[Segment]) -> str:
    blocks = [
        f"{index}\n{format_timestamp(seg.start)} --> {format_timestamp(seg.end)}\n{seg.text}\n"
        for index, seg in enumerate(segments, start=1)
    ]
    return "\n".join(blocks)


def write_srt(segments: Sequence[Segment], path: Path) -> None:
    path.write_text(to_srt(segments), encoding="utf-8")
