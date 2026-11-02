import ctypes
import importlib.util
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


# Load order matters: libcublas.so.12 depends on libcublasLt.so.12.
_LINUX_NVIDIA_LIBS = ("cublas/lib/libcublasLt.so.12", "cublas/lib/libcublas.so.12", "cudnn/lib/libcudnn.so.9")


def _add_nvidia_dll_dirs() -> None:
    """Make the cuBLAS/cuDNN libraries from the nvidia-* wheels loadable.

    The wheels install them under site-packages/nvidia/<lib>, which neither Windows
    nor the Linux dynamic loader searches, so ctranslate2 fails with
    "cublas64_12.dll is not found" or "libcublas.so.12 is not found".
    """
    if sys.platform not in ("win32", "linux"):
        return
    spec = importlib.util.find_spec("nvidia")
    if spec is None or spec.submodule_search_locations is None:
        return
    for root in spec.submodule_search_locations:
        if sys.platform == "linux":
            # LD_LIBRARY_PATH is only read at process start, so preload the libraries
            # globally; ctranslate2's later dlopen by soname then finds them loaded.
            for lib in _LINUX_NVIDIA_LIBS:
                lib_path = Path(root) / lib
                if lib_path.exists():
                    ctypes.CDLL(str(lib_path), mode=ctypes.RTLD_GLOBAL)
            continue
        for bin_dir in Path(root).glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            # ctranslate2 loads cuBLAS lazily with a plain LoadLibrary, which uses PATH.
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"


_add_nvidia_dll_dirs()

import ctranslate2  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Transcript:
    source_language: str
    segments: list[Segment]


ProgressCallback = Callable[[float, float], None]


def resolve_device(device: str) -> str:
    if device != "auto":
        return device
    return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"


def load_model(model_size: str, device: str) -> WhisperModel:
    compute_type = "float16" if device == "cuda" else "int8"
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe_file(
    model_size: str,
    media_path: Path,
    source_language: str | None,
    device: str,
    on_progress: ProgressCallback | None = None,
    vad_filter: bool = True,
) -> Transcript:
    """Load the model and transcribe, falling back to CPU if CUDA cannot run.

    CUDA can be detected but still fail at runtime when the cuBLAS/cuDNN libraries
    are missing, so the failure is only seen once transcription starts.
    """
    resolved = resolve_device(device)
    try:
        model = load_model(model_size, resolved)
        return transcribe_to_english(model, media_path, source_language, on_progress, vad_filter)
    except RuntimeError as error:
        if resolved != "cuda":
            raise
        print(f"warning: CUDA failed ({error}); retrying on CPU (slower)", file=sys.stderr)
        model = load_model(model_size, "cpu")
        return transcribe_to_english(model, media_path, source_language, on_progress, vad_filter)


def transcribe_to_english(
    model: WhisperModel,
    media_path: Path,
    source_language: str | None = None,
    on_progress: ProgressCallback | None = None,
    vad_filter: bool = True,
) -> Transcript:
    """Return English segments for the media file.

    Non-English speech is translated by Whisper's `translate` task; English speech
    is transcribed as-is. `vad_filter` skips non-speech audio before transcribing,
    which cuts down on hallucinated text during silence or music.
    """
    if source_language is None:
        # Passing no language makes faster-whisper detect it; the generator is not consumed.
        _, info = model.transcribe(str(media_path), task="transcribe", vad_filter=vad_filter)
        source_language = info.language

    task = "transcribe" if source_language == "en" else "translate"
    raw_segments, info = model.transcribe(
        str(media_path),
        language=source_language,
        task=task,
        vad_filter=vad_filter,
        beam_size=5,
    )

    segments: list[Segment] = []
    for raw in raw_segments:
        text = raw.text.strip()
        if text:
            segments.append(Segment(start=raw.start, end=raw.end, text=text))
        if on_progress:
            on_progress(raw.end, info.duration)

    return Transcript(source_language=source_language, segments=segments)
