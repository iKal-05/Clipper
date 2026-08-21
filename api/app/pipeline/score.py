"""Score stage: combine visual/audio features into moments."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List

from app.services.pipeline_runner import StageContext

logger = logging.getLogger(__name__)


def _tfidf_score(text: str) -> float:
    return min(100.0, len(text) * 0.5)


def _prosody_score(pitch: List[float]) -> float:
    """Normalize pitch (Hz) to 0-100. Human speech ~85-300Hz."""
    if not pitch:
        return 0.0
    avg = sum(pitch) / len(pitch)
    return min(100.0, max(0.0, (avg - 85) / (300 - 85) * 100))


def _visual_score(motion: float) -> float:
    return min(100.0, motion * 100.0)


import math


async def run(ctx: StageContext) -> List[dict]:
    """Read analysis.json, compute moments, split long chunks, write moments.json."""
    storage = Path(ctx.storage_dir)
    analysis_path = storage / "analysis.json"
    if not analysis_path.exists():
        raise RuntimeError("analysis.json missing")
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))

    max_sec = ctx.prefs.max_clip_seconds
    moments: List[dict] = []
    audio_energy = analysis.get("audio", {}).get("energy", [])
    audio_pitch = analysis.get("audio", {}).get("pitch", [])

    for chunk in analysis.get("visual", {}).get("chunks", []):
        chunk_start = chunk["start"]
        chunk_end = chunk["end"]
        motion = chunk.get("motion_avg", 0.0)
        chunk_dur = chunk_end - chunk_start

        # Split long chunks into sub-moments of at most max_clip_seconds
        num_segments = max(1, int(math.ceil(chunk_dur / max_sec))) if chunk_dur > max_sec else 1
        seg_dur = chunk_dur / num_segments

        for si in range(num_segments):
            seg_start = chunk_start + si * seg_dur
            seg_end = min(seg_start + seg_dur, chunk_end)
            idx = int(seg_start * 10)
            energy = audio_energy[idx] if idx < len(audio_energy) else 0.0
            pitch_val = audio_pitch[idx] if idx < len(audio_pitch) else 0.0
            score = (
                0.4 * _visual_score(motion)
                + 0.3 * _prosody_score([pitch_val])
                + 0.3 * min(100.0, energy * 100.0)
            )
            score = min(100.0, max(0.0, score))
            label = "Aha" if score > 70 else "Insight"
            moments.append({
                "label": label,
                "start": round(seg_start, 2),
                "end": round(seg_end, 2),
                "score": round(score, 2),
                "evidence": {"motion": motion, "energy": energy, "pitch": pitch_val},
            })

        if audio_energy:
            await ctx.progress_cb(min(0.9, chunk_end / 200.0), f"Scoring chunk {len(moments)}")

    out_path = storage / "moments.json"
    out_path.write_text(json.dumps(moments, ensure_ascii=False), encoding="utf-8")
    await ctx.progress_cb(1.0, "Scoring complete")
    return moments
