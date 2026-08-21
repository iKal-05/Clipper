"""Subtitle stage: slice transcript per candidate, write ASS files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.services.pipeline_runner import StageContext

logger = logging.getLogger(__name__)


async def run(ctx: StageContext) -> list[dict[str, Any]]:
    """Read transcript.json + candidates.json, write per-candidate ASS subs."""
    storage = Path(ctx.storage_dir)
    transcript_path = storage / "transcript.json"
    candidates_path = storage / "candidates.json"

    if not transcript_path.exists() or not candidates_path.exists():
        raise RuntimeError("transcript.json or candidates.json missing")

    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))

    segments = transcript.get("segments", [])
    subtitle_files = []

    for cand in candidates:
        clip_id = cand["candidate_id"]
        start = cand["start"]
        end = cand["end"]

        # Slice segments within [start, end]
        clip_segments = []
        for seg in segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            if seg_end <= start:
                continue
            if seg_start >= end:
                break
            # Clip to candidate boundaries
            s = max(seg_start, start) - start
            e = min(seg_end, end) - start
            clip_segments.append({"start": s, "end": e, "text": seg["text"]})

        # Write ASS file
        ass_path = storage / "clips" / f"{clip_id}.ass"
        ass_path.parent.mkdir(exist_ok=True)
        _write_ass(ass_path, clip_segments)

        subtitle_files.append({
            "candidate_id": clip_id,
            "subtitle_path": str(ass_path),
            "segments": clip_segments,
        })
        await ctx.progress_cb((candidates.index(cand) + 1) / len(candidates), f"Subtitles: {clip_id}")

    # Write manifest
    manifest_path = storage / "subtitles.json"
    manifest_path.write_text(json.dumps(subtitle_files, ensure_ascii=False), encoding="utf-8")

    await ctx.progress_cb(1.0, f"Subtitle stage: {len(subtitle_files)} files")
    return subtitle_files


def _write_ass(path: Path, segments: list[dict[str, Any]]) -> None:
    """Write ASS subtitle with WCAG AA contrast styling."""
    # ASS header with style: white text, black outline (3px), black shadow (4px)
    header = """[Script Info]
Title: Clipper Subtitles
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,4,2,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def fmt_time(t: float) -> str:
        """Convert seconds to ASS time format H:MM:SS.cc"""
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        cs = int((t * 100) % 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    lines = [header]
    for seg in segments:
        start = fmt_time(seg["start"])
        end = fmt_time(seg["end"])
        text = seg["text"].replace("\n", "\\N")
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    path.write_text("\n".join(lines), encoding="utf-8")