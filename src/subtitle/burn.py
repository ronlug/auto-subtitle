import functools
import shutil
import subprocess
import sys
from pathlib import Path

SUBTITLE_STYLE = "Alignment=2,FontSize=24,Outline=2,Shadow=1"

# Burning re-encodes every frame, so the encoder dominates the run time.
ENCODER_ARGS = {
    "nvenc": ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "23", "-b:v", "0"],
    "x264": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"],
}


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg was not found on PATH. Install it (e.g. `winget install Gyan.FFmpeg`) "
            "to add subtitles to the video."
        )


@functools.cache
def nvenc_available() -> bool:
    """True if ffmpeg can actually encode with NVENC (build support and a usable GPU)."""
    probe = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=s=256x256:d=0.1",
        "-c:v", "h264_nvenc", "-f", "null", "-",
    ]
    return subprocess.run(probe, capture_output=True).returncode == 0


def resolve_encoder(encoder: str) -> str:
    if encoder != "auto":
        return encoder
    return "nvenc" if nvenc_available() else "x264"


def escape_filter_path(path: Path) -> str:
    """Escape a path for use inside an ffmpeg filter argument (e.g. `subtitles=...`)."""
    escaped = path.resolve().as_posix()
    for char in ("\\", ":", "'", "[", "]", ","):
        escaped = escaped.replace(char, "\\" + char)
    return escaped


def burn_command(video: Path, srt: Path, output: Path, encoder: str) -> list[str]:
    video_filter = f"subtitles='{escape_filter_path(srt)}':force_style='{SUBTITLE_STYLE}'"
    return [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video),
        "-vf", video_filter,
        *ENCODER_ARGS[encoder],
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        str(output),
    ]


def burn_subtitles(video: Path, srt: Path, output: Path, encoder: str = "auto") -> str:
    """Re-encode `video` with `srt` rendered at the bottom-centre. Returns the encoder used."""
    require_ffmpeg()
    encoder = resolve_encoder(encoder)
    try:
        subprocess.run(burn_command(video, srt, output, encoder), check=True)
    except subprocess.CalledProcessError:
        if encoder != "nvenc":
            raise
        print("warning: NVENC encode failed; retrying with libx264 (slower)", file=sys.stderr)
        encoder = "x264"
        subprocess.run(burn_command(video, srt, output, encoder), check=True)
    return encoder


def embed_command(video: Path, srt: Path, output: Path) -> list[str]:
    return [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video),
        "-i", str(srt),
        "-map", "0:v", "-map", "0:a?", "-map", "1:0",
        "-c", "copy",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=eng",
        "-disposition:s:0", "default",
        str(output),
    ]


def embed_subtitles(video: Path, srt: Path, output: Path) -> None:
    """Add `srt` as a selectable subtitle track without re-encoding (fast)."""
    require_ffmpeg()
    subprocess.run(embed_command(video, srt, output), check=True)
