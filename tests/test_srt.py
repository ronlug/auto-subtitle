from subtitle.srt import format_timestamp, to_srt
from subtitle.transcribe import Segment


def test_format_timestamp_handles_hours_and_millis():
    assert format_timestamp(0) == "00:00:00,000"
    assert format_timestamp(3661.5) == "01:01:01,500"
    assert format_timestamp(59.9996) == "00:01:00,000"


def test_to_srt_numbers_blocks_from_one():
    segments = [
        Segment(start=0.0, end=1.5, text="Hello"),
        Segment(start=2.0, end=3.25, text="World"),
    ]

    assert to_srt(segments) == (
        "1\n00:00:00,000 --> 00:00:01,500\nHello\n"
        "\n"
        "2\n00:00:02,000 --> 00:00:03,250\nWorld\n"
    )
