import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from subtitle.burn import burn_subtitles, embed_subtitles, require_ffmpeg
from subtitle.download import download, is_url
from subtitle.srt import write_srt
from subtitle.transcribe import transcribe_file


MODES = ("file", "burn", "soft")


def _modes(value: str) -> list[str]:
    """Parse one --mode value, which may itself be comma-separated (e.g. "burn,soft")."""
    modes = [mode.strip() for mode in value.split(",") if mode.strip()]
    invalid = [mode for mode in modes if mode not in MODES]
    if not modes or invalid:
        raise argparse.ArgumentTypeError(
            f"invalid mode {value!r} (choose from {', '.join(MODES)}; "
            "put the video before --mode, or separate modes with commas)"
        )
    return modes


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="subtitle",
        description="Download a video (or use a local file) and create English subtitles.",
    )
    parser.add_argument("input", help="Video file path or video URL")
    parser.add_argument(
        "--mode",
        type=_modes,
        nargs="+",
        metavar="MODE",
        help=(
            "One or more outputs, space- or comma-separated (default: file). "
            "file: separate .srt file; burn: subtitles drawn into the video picture; "
            "soft: subtitle track added to the video (no re-encode, fast). "
            "Example: --mode file burn soft"
        ),
    )
    parser.add_argument(
        "--encoder",
        choices=["auto", "nvenc", "x264"],
        default="auto",
        help="Video encoder for --mode burn: auto uses NVIDIA NVENC when available",
    )
    parser.add_argument(
        "--model",
        default="small",
        help="Whisper model size: tiny, base, small, medium, large-v3 (default: small)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Source language code (e.g. th, ja). Detected automatically when omitted.",
    )
    parser.add_argument(
        "--vad",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip non-speech audio before transcribing (default: on). Use --no-vad "
        "if quiet or overlapping speech is being dropped.",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cuda", "cpu"],
        default="auto",
        help="Compute device for transcription (default: auto)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for downloads and results (default: ./output)",
    )
    args = parser.parse_args(argv)
    # Flatten "--mode burn,soft file" into ["burn", "soft", "file"], dropping duplicates.
    groups = args.mode or [["file"]]
    args.mode = list(dict.fromkeys(mode for group in groups for mode in group))
    return args


def _print_progress(end: float, duration: float) -> None:
    if duration > 0:
        print(f"\r  transcribed {end:7.1f}s / {duration:.1f}s", end="", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if "burn" in args.mode or "soft" in args.mode:
            require_ffmpeg()  # fail before doing any slow work

        output_dir: Path = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        if is_url(args.input):
            print(f"Downloading {args.input} ...")
            video = download(args.input, output_dir)
            print(f"Saved video: {video}")
        else:
            video = Path(args.input)
            if not video.is_file():
                raise FileNotFoundError(f"Input file not found: {video}")

        print(f"Transcribing with Whisper '{args.model}' (translating to English if needed) ...")
        transcript = transcribe_file(
            args.model, video, args.language, args.device, _print_progress, vad_filter=args.vad
        )
        print(file=sys.stderr)
        print(f"Source language: {transcript.source_language}, {len(transcript.segments)} segments")

        with tempfile.TemporaryDirectory() as tmp:
            # Without "file", the .srt is only needed while ffmpeg runs, so it goes to a temp dir.
            if "file" in args.mode:
                srt_path = output_dir / f"{video.stem}.en.srt"
            else:
                srt_path = Path(tmp) / "subtitles.srt"
            write_srt(transcript.segments, srt_path)
            if "file" in args.mode:
                print(f"Subtitle file: {srt_path}")

            if "burn" in args.mode:
                burned = output_dir / f"{video.stem}.en.burned.mp4"
                print("Burning subtitles into video ...")
                encoder = burn_subtitles(video, srt_path, burned, args.encoder)
                print(f"Video with subtitles ({encoder}): {burned}")

            if "soft" in args.mode:
                embedded = output_dir / f"{video.stem}.en.soft.mp4"
                print("Adding subtitle track to video ...")
                embed_subtitles(video, srt_path, embedded)
                print(f"Video with subtitle track: {embedded}")
    except subprocess.CalledProcessError as error:
        print(f"error: ffmpeg failed (exit code {error.returncode})", file=sys.stderr)
        return 1
    except (RuntimeError, FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0
