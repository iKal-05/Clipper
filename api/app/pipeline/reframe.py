"""Reframe stage: compute 9:16 crop transforms from face tracks."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.services.pipeline_runner import StageContext

logger = logging.getLogger(__name__)

TARGET_W, TARGET_H = 720, 1280  # 9:16


async def run(ctx: StageContext) -> list[dict[str, Any]]:
    """Read analysis.json face_tracks + candidates.json, compute reframe plan per candidate."""
    storage = Path(ctx.storage_dir)
    analysis_path = storage / "analysis.json"
    candidates_path = storage / "candidates.json"

    if not candidates_path.exists():
        raise RuntimeError("candidates.json missing")

    analysis = {}
    if analysis_path.exists():
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))

    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    face_tracks = analysis.get("visual", {}).get("face_tracks", [])

    plans = []
    for c in candidates:
        start, end = c["start"], c["end"]
        # Find face tracks in this time window
        tracks = [t for t in face_tracks if start <= t["time"] <= end]
        if tracks:
            # Average face position
            avg_x = sum(t["x"] for t in tracks) / len(tracks)
            avg_y = sum(t["y"] for t in tracks) / len(tracks)
        else:
            # Center crop fallback
            avg_x, avg_y = 0.5, 0.5

        # Source dimensions from analysis
        src_w = analysis.get("visual", {}).get("width", 1920)
        src_h = analysis.get("visual", {}).get("height", 1080)
        if src_w == 0 or src_h == 0:
            src_w, src_h = 1920, 1080  # fallback

        # Compute crop: want 9:16 = 0.5625 aspect
        target_aspect = TARGET_W / TARGET_H  # 0.5625
        src_aspect = src_w / src_h

        if src_aspect > target_aspect:
            # Source wider than target -> crop width
            crop_h = src_h
            crop_w = int(src_h * target_aspect)
        else:
            # Source taller -> crop height
            crop_w = src_w
            crop_h = int(src_w / target_aspect)

        # Clamp crop dimensions to source (defense-in-depth for wrong analysis dims)
        crop_w = min(crop_w, src_w)
        crop_h = min(crop_h, src_h)

        # Center crop box in source coordinates, shifted to face
        cx = int(avg_x * src_w)
        cy = int(avg_y * src_h)
        x1 = max(0, min(cx - crop_w // 2, src_w - crop_w))
        y1 = max(0, min(cy - crop_h // 2, src_h - crop_h))

        plans.append({
            "candidate_id": c["candidate_id"],
            "source_crop": {"x": x1, "y": y1, "w": crop_w, "h": crop_h},
            "target_size": {"w": TARGET_W, "h": TARGET_H},
            "zoom": {"enabled": True, "center": {"x": avg_x, "y": avg_y}, "peak_time": (start + end) / 2},
        })

    out_path = storage / "reframe.json"
    out_path.write_text(json.dumps(plans, ensure_ascii=False), encoding="utf-8")
    await ctx.progress_cb(1.0, f"Reframe: {len(plans)} plans")
    return plans