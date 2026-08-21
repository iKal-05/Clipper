"""Cut stage: select top-N candidates from moments."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.services.pipeline_runner import StageContext

logger = logging.getLogger(__name__)


async def run(ctx: StageContext) -> list[dict[str, Any]]:
    """Read moments.json, pick candidates, write candidates.json, return list."""
    storage = Path(ctx.storage_dir)
    moments_path = storage / "moments.json"
    if not moments_path.exists():
        raise RuntimeError("moments.json missing")
    moments = json.loads(moments_path.read_text(encoding="utf-8"))

    max_clips = ctx.prefs.max_clips
    max_sec = ctx.prefs.max_clip_seconds
    min_score = ctx.prefs.min_score or 0.0

    # Filter by min_score and duration ≤ max_sec
    filtered = [m for m in moments if m["score"] >= min_score and (m["end"] - m["start"]) <= max_sec]

    # Sort by score desc
    filtered.sort(key=lambda x: x["score"], reverse=True)

    # Top N
    candidates = filtered[:max_clips]

    # Add candidate IDs
    for i, c in enumerate(candidates):
        c["candidate_id"] = f"clip_{i+1}"

    out_path = storage / "candidates.json"
    out_path.write_text(json.dumps(candidates, ensure_ascii=False), encoding="utf-8")
    await ctx.progress_cb(1.0, f"Cut stage: {len(candidates)} candidates")
    return candidates