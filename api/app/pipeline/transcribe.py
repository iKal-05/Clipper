"""Transcribe stage: Whisper integration."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from app.services.pipeline_runner import StageContext

logger = logging.getLogger(__name__)


async def run(ctx: StageContext) -> list[dict]:
    """Run Whisper transcription on ctx.storage_dir/audio.wav.

    Writes transcript.json and returns list of segment dicts: {"start", "end", "text"}.
    """
    storage = Path(ctx.storage_dir)
    audio_path = storage / "audio.wav"
    model_name = ctx.prefs.whisper_model
    # lazy import; whisper optional dep
    try:
        import whisper
    except Exception:
        logger.warning("Whisper not installed — writing empty transcript (pipeline continues)")
        segments: list[dict] = []
        _write_transcript(storage, segments)
        await ctx.progress_cb(1.0, "Transcription skipped (Whisper not installed)")
        return segments

    logger.info("Loading Whisper model %s", model_name)
    model = whisper.load_model(model_name)
    logger.info("Transcribing %s", audio_path)
    result = await asyncio.to_thread(model.transcribe, str(audio_path))
    segments = [
        {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
        for seg in result.get("segments", [])
    ]
    _write_transcript(storage, segments)
    await ctx.progress_cb(1.0, "Transcription complete")
    return segments


def _write_transcript(storage: Path, segments: list[dict]) -> None:
    """Persist transcript.json for downstream stages (subtitle, assets)."""
    transcript = {"segments": segments}
    out = storage / "transcript.json"
    out.write_text(json.dumps(transcript, ensure_ascii=False), encoding="utf-8")
