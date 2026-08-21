"""Download stage: yt-dlp video + audio extraction."""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.services.pipeline_runner import StageContext

logger = logging.getLogger(__name__)


@dataclass
class MediaMeta:
    source_path: str
    audio_path: str
    duration: float
    width: int
    height: int
    fps: float


URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def extract_video_id(url: str) -> str | None:
    m = URL_RE.search(url)
    return m.group(1) if m else None


def _resolve_binary(name: str, configured: str | None = None) -> str:
    """Resolve binary path: prefer configured, then look in PATH. Raise if missing."""
    if configured:
        if Path(configured).exists():
            return configured
        found_cfg = shutil.which(configured)
        if found_cfg:
            return found_cfg
        raise FileNotFoundError(f"Configured binary '{configured}' not found in PATH.")
    found = shutil.which(name)
    if not found:
        raise FileNotFoundError(
            f"Required binary '{name}' not found in PATH. Install it or set in config."
        )
    return found


async def _stream_subprocess(
    ctx: StageContext,
    proc: asyncio.subprocess.Process,
    *,
    progress_phase: float,
    progress_max: float,
) -> bytes:
    """Read stdout and stderr concurrently; parse yt‑dlp progress; return full stdout."""
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []

    async def _read(stream: asyncio.StreamReader, sink: list[bytes]) -> None:
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                return
            sink.append(chunk)

    async def _parse_progress() -> None:
        buf = b""
        pct_re = re.compile(rb"\[download\]\s+(\d{1,3}\.\d)%")
        while True:
            await asyncio.sleep(0.5)
            if stdout_chunks or stderr_chunks:
                buf += b"".join(stdout_chunks + stderr_chunks)
                stdout_chunks.clear()
                stderr_chunks.clear()
            m = pct_re.search(buf)
            if m:
                try:
                    pct = float(m.group(1))
                except ValueError:
                    continue
                mapped = (progress_phase + (pct / 100.0) * (progress_max - progress_phase))
                await ctx.progress_cb(mapped/100.0, f"Downloading... {pct:.1f}%")
                buf = buf[m.end():]
            if proc.returncode is not None and not stdout_chunks and not stderr_chunks:
                return

    tasks = []
    if proc.stdout is not None:
        tasks.append(asyncio.create_task(_read(proc.stdout, stdout_chunks)))
    if proc.stderr is not None:
        tasks.append(asyncio.create_task(_read(proc.stderr, stderr_chunks)))
    progress_task = asyncio.create_task(_parse_progress())
    rc = await proc.wait()
    for t in tasks:
        await t
    progress_task.cancel()
    try:
        await progress_task
    except Exception:
        pass
    return b"".join(stdout_chunks + stderr_chunks)



async def run(ctx: StageContext) -> MediaMeta:
    """Download best video+audio, extract audio to wav, return metadata."""
    url = ctx.url
    vid = extract_video_id(url)
    if not vid:
        raise ValueError(f"Invalid YouTube URL: {url}")
    out_dir = Path(ctx.storage_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    source_path = out_dir / "source.mp4"
    audio_path = out_dir / "audio.wav"

    settings = get_settings()
    yt_dlp_bin = _resolve_binary("yt-dlp")
    ffmpeg_bin = _resolve_binary("ffmpeg", settings.ffmpeg_binary)

    await ctx.progress_cb(0.0, "Starting download")
    await ctx.log("info", f"Downloading: {url}")

    # yt-dlp: best video + best audio, merge to mp4
    cmd = [
        yt_dlp_bin,
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "--no-part",
        "--newline",  # one progress line per line (parseable)
        "-o",
        str(source_path),
        url,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out = await _stream_subprocess(ctx, proc, progress_phase=0.0, progress_max=0.6)
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed (exit {proc.returncode}): {out.decode(errors='replace')[:2000]}")
    if not source_path.exists() or source_path.stat().st_size == 0:
        raise RuntimeError(f"yt-dlp reported success but {source_path} missing or empty.")

    await ctx.progress_cb(0.6, "Download complete, extracting audio")
    await ctx.log("info", "Audio extraction starting")

    # ffmpeg extract audio to wav (16kHz mono for Whisper)
    ffmpeg_cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-sample_fmt",
        "s16",
        str(audio_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    stderr, _ = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extract failed: {stderr.decode(errors='replace')[:2000]}")
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg reported success but {audio_path} missing or empty.")

    await ctx.progress_cb(0.8, "Probing media")
    # Probe metadata
    meta = await _probe_media(source_path)
    await ctx.progress_cb(1.0, "Download stage done")
    return MediaMeta(
        source_path=str(source_path),
        audio_path=str(audio_path),
        duration=meta["duration"],
        width=meta["width"],
        height=meta["height"],
        fps=meta["fps"],
    )


async def _probe_media(path: Path) -> dict:
    """ffprobe to get duration, width, height, fps."""
    settings = get_settings()
    ffprobe_bin = _resolve_binary("ffprobe", settings.ffprobe_binary)

    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {"duration": 0, "width": 0, "height": 0, "fps": 0}
    import json

    data = json.loads(stdout.decode())
    stream = data.get("streams", [{}])[0]
    fmt = data.get("format", {})
    w = stream.get("width", 0)
    h = stream.get("height", 0)
    fps = _parse_fps(stream.get("r_frame_rate", "0/1"))
    # Prefer format duration (more reliable), fall back to stream
    dur = float(fmt.get("duration", stream.get("duration", 0)))
    return {"duration": dur, "width": w, "height": h, "fps": fps}


def _parse_fps(rate: str) -> float:
    try:
        num, den = map(int, rate.split("/"))
        return num / den if den else 0.0
    except Exception:
        return 0.0