from pathlib import Path

import yt_dlp


def is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def download(url: str, output_dir: Path) -> Path:
    """Download the best audio+video for `url` into `output_dir` and return the file path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    options = {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": str(output_dir / "%(title).150B [%(id)s].%(ext)s"),
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))

    # When yt-dlp merges streams, the final file is the merge output format.
    if not path.exists():
        path = path.with_suffix(".mp4")
    if not path.exists():
        raise FileNotFoundError(f"yt-dlp finished but the file was not found: {path}")
    return path
