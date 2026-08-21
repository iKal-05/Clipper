"""Render stage: ffmpeg pipeline to produce final clips."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from app.services.pipeline_runner import StageContext

logger = logging.getLogger(__name__)


async def run(ctx: StageContext) -> list[dict[str, Any]]:
    """Read reframe.json + candidates.json, render each clip via ffmpeg."""
    storage = Path(ctx.storage_dir)
    reframe_path = storage / "reframe.json"
    candidates_path = storage / "candidates.json"

    if not reframe_path.exists() or not candidates_path.exists():
        raise RuntimeError("reframe.json or candidates.json missing")

    plans = json.loads(reframe_path.read_text(encoding="utf-8"))
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))

    clips_dir = storage / "clips"
    clips_dir.mkdir(exist_ok=True)

    results = []
    for i, (plan, cand) in enumerate(zip(plans, candidates)):
        clip_id = plan["candidate_id"]
        out_path = clips_dir / f"{clip_id}.mp4"
        await _render_clip(ctx, plan, cand, out_path)
        results.append({
            "clip_id": clip_id,
            "video_path": str(out_path),
            "start": cand["start"],
            "end": cand["end"],
            "duration": cand["end"] - cand["start"],
            "score": cand["score"],
        })
        await ctx.progress_cb((i + 1) / len(plans), f"Rendered {clip_id}")

    # Write clip metadata for assets stage
    meta_path = storage / "clips.json"
    meta_path.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")

    await ctx.progress_cb(1.0, f"Render complete: {len(results)} clips")
    return results


async def _render_clip(ctx: StageContext, plan: dict, cand: dict, out_path: Path) -> None:
    """Build ffmpeg filter graph and render."""
    source = Path(ctx.storage_dir) / "source.mp4"
    crop = plan["source_crop"]
    target = plan["target_size"]
    zoom = plan.get("zoom", {})

    # Build filter chain
    filters = []
    # 1. Crop
    filters.append(f"crop={crop['w']}:{crop['h']}:{crop['x']}:{crop['y']}")
    # 2. Scale to target
    filters.append(f"scale={target['w']}:{target['h']}:flags=lanczos")
    # 3. Zoom (Ken Burns): gentle slow zoom-in. zoompan runs at `fps` frames/s.
    if zoom.get("enabled"):
        filters.append(
            f"zoompan=z='min(zoom+0.0008,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:fps=30:s={target['w']}x{target['h']}"
        )
    # 4. Pad to exact 9:16 if needed (should already match)
    filter_graph = ",".join(filters)

    # Trim timestamps
    start = cand["start"]
    duration = cand["end"] - cand["start"]

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-t",
        str(duration),
        "-i",
        str(source),
        "-vf",
        filter_graph,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(out_path),
    ]

    logger.info("Rendering clip: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode()
        logger.error("FFMPEG stderr: %s", err)
        raise RuntimeError(f"ffmpeg render failed: {err}")