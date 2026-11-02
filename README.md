# subtitle

Give it a video file or a video URL and it produces **English subtitles**. Speech in other
languages is translated to English. Subtitles can be saved as a separate `.srt` file, burned
into the bottom of the video, or both.

- Downloads from URLs with [yt-dlp](https://github.com/yt-dlp/yt-dlp) (any site it supports)
- Transcribes and translates locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (no API key)
- Burns subtitles in with ffmpeg

## Requirements

- [uv](https://docs.astral.sh/uv/)
- [ffmpeg](https://ffmpeg.org/) on your PATH (needed for `--mode burn|both`, and for yt-dlp to merge video and audio)
  - Windows: `winget install Gyan.FFmpeg`
- Optional: an NVIDIA GPU with CUDA for faster transcription. Without working CUDA libraries the tool falls back to CPU automatically.

## Setup

```bash
uv sync
```

## Usage

```bash
# Separate .srt file (default)
uv run subtitle "https://www.youtube.com/watch?v=..." --mode file

# Subtitles burned into the video at the bottom (re-encodes the video)
uv run subtitle video.mp4 --mode burn

# Subtitles added as a track players can toggle (no re-encode, takes seconds)
uv run subtitle video.mp4 --mode soft

# Several outputs at once (space- or comma-separated)
uv run subtitle video.mp4 --mode file burn soft
uv run subtitle video.mp4 --mode burn,soft
```

Put the video before `--mode` when listing modes with spaces, otherwise it is read as a mode.

Results go to `./output` by default (change with `--output-dir`).

| Option | Default | Meaning |
| --- | --- | --- |
| `input` | required | Local video path or URL |
| `--mode` | `file` | One or more of: `file` = `.srt` file, `burn` = subtitles drawn into the picture, `soft` = subtitle track in the video |
| `--encoder` | `auto` | Encoder for burning: `auto` uses NVIDIA NVENC when available, else `x264` |
| `--model` | `small` | Whisper size: `tiny`, `base`, `small`, `medium`, `large-v3` (bigger = more accurate, slower) |
| `--language` | auto | Source language code such as `th` or `ja`, if auto-detection gets it wrong |
| `--vad` / `--no-vad` | on | Skip non-speech audio before transcribing. Reduces made-up text during silence/music; turn off if quiet speech is being missed |
| `--device` | `auto` | `auto`, `cuda`, or `cpu` |
| `--output-dir` | `output` | Where downloads and results are written |

The first run downloads the chosen Whisper model from Hugging Face and caches it.

Output names: `<name>.en.srt` (file), `<name>.en.burned.mp4` (burn), `<name>.en.soft.mp4` (soft).

Burning has to re-encode every frame, so it is the slowest step. With an NVIDIA GPU it uses
NVENC (falling back to libx264 if NVENC fails). `soft` mode skips re-encoding entirely, but the
subtitles are a track the player shows, not part of the picture.

## Development

```bash
uv run pytest
```
