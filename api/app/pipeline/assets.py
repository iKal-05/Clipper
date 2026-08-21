"""Asset stage: generate titles, hooks, descriptions, hashtags, thumbnails, keywords."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.services.pipeline_runner import StageContext

logger = logging.getLogger(__name__)


async def run(ctx: StageContext) -> list[dict[str, Any]]:
    """Read clips.json + transcript.json + moments.json, generate Asset per clip."""
    storage = Path(ctx.storage_dir)
    clips_path = storage / "clips.json"
    transcript_path = storage / "transcript.json"
    moments_path = storage / "moments.json"

    if not clips_path.exists() or not transcript_path.exists() or not moments_path.exists():
        raise RuntimeError("clips.json, transcript.json, or moments.json missing")

    clips = json.loads(clips_path.read_text(encoding="utf-8"))
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    moments = json.loads(moments_path.read_text(encoding="utf-8"))

    full_text = " ".join(seg["text"] for seg in transcript.get("segments", []))
    keywords = _extract_keywords(full_text)

    assets = []
    for i, clip in enumerate(clips):
        clip_id = clip["clip_id"]
        score = clip["score"]
        moment_labels = _get_moment_labels(moments, clip["start"], clip["end"])

        title = _generate_title(full_text, moment_labels, score)
        hook = _generate_hook(full_text)
        description = _generate_description(full_text, clip_id)
        hashtags = _generate_hashtags(keywords)
        platform_tags = ["YouTube Shorts", "TikTok", "Instagram Reels", "Facebook Reels"]
        thumbnail_path = await _generate_thumbnail(ctx, clip, title)
        asset_keywords = keywords[:10]

        asset = {
            "clip_id": clip_id,
            "title": title,
            "hook": hook,
            "description": description,
            "hashtags": hashtags,
            "platform_tags": platform_tags,
            "thumbnail_path": thumbnail_path,
            "keywords": asset_keywords,
        }
        assets.append(asset)

        # Write individual asset file
        asset_dir = storage / "assets" / clip_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        (asset_dir / "asset.json").write_text(json.dumps(asset, ensure_ascii=False), encoding="utf-8")

        await ctx.progress_cb((i + 1) / len(clips), f"Assets: {clip_id}")

    # Write manifest
    manifest_path = storage / "assets.json"
    manifest_path.write_text(json.dumps(assets, ensure_ascii=False), encoding="utf-8")

    await ctx.progress_cb(1.0, f"Assets stage: {len(assets)} assets")
    return assets


def _extract_keywords(text: str) -> list[str]:
    """Simple TF-IDF-like keyword extraction (placeholder)."""
    import re
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    stopwords = {"the", "and", "you", "that", "this", "with", "for", "are", "not", "but", "from", "have", "has", "been", "will", "your", "what", "when", "where", "who", "how", "why", "can", "just", "like", "think", "know", "really", "very", "more", "also", "even", "then", "than", "their", "there", "about", "would", "could", "should", "because", "something", "anything", "everything", "nothing"}
    freq = {}
    for w in words:
        if w not in stopwords:
            freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:20]]


def _get_moment_labels(moments: list[dict], start: float, end: float) -> list[str]:
    labels = []
    for m in moments:
        if m["start"] < end and m["end"] > start:
            labels.append(m["label"])
    return labels or ["Aha"]


def _generate_title(text: str, labels: list[str], score: float) -> str:
    words = text.split()[:30]
    base = " ".join(words[:8])
    label_str = labels[0] if labels else "Moment"
    title = f"{label_str}: {base}..."
    return title[:100]


def _generate_hook(text: str) -> str:
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
    if sentences:
        return " ".join(sentences[0].split()[:15]) + "..."
    return " ".join(text.split()[:15]) + "..."


def _generate_description(text: str, clip_id: str) -> str:
    snippet = " ".join(text.split()[:100])
    cta = "\n\n💡 Follow for more! #Shorts #Viral"
    return f"{snippet}...{cta}"[:5000]


def _generate_hashtags(keywords: list[str]) -> list[str]:
    base = ["shorts", "viral", "trending", "fyp", "foryou"]
    kw_tags = [k.replace(" ", "") for k in keywords[:10]]
    return (base + kw_tags)[:15]


async def _generate_thumbnail(ctx: StageContext, clip: dict, title: str) -> str:
    """Extract best frame from video + overlay title using PIL."""
    storage = Path(ctx.storage_dir)
    source = storage / "source.mp4"
    clips_dir = storage / "clips"
    clips_dir.mkdir(exist_ok=True)

    thumb_path = clips_dir / f"{clip['clip_id']}_thumb.jpg"

    # Use ffmpeg to extract frame at midpoint
    mid_time = clip["start"] + clip["duration"] / 2
    import asyncio
    cmd = [
        "ffmpeg", "-y", "-ss", str(mid_time), "-i", str(source),
        "-vframes", "1", "-q:v", "2", "-update", "1", str(thumb_path)
    ]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error("FFMPEG thumbnail failed for %s: %s", clip['clip_id'], stderr.decode())
        return str(thumb_path)

    # Overlay title if frame extracted
    if thumb_path.exists() and thumb_path.stat().st_size > 0:
        try:
            img = Image.open(thumb_path).convert("RGBA")
            draw = ImageDraw.Draw(img)

            # Try to load font
            try:
                font = ImageFont.truetype("arial.ttf", 36)
            except Exception:
                font = ImageFont.load_default()

            # Draw semi-transparent background bar at bottom
            bar_h = 120
            bar = Image.new("RGBA", (img.width, bar_h), (0, 0, 0, 180))
            img.paste(bar, (0, img.height - bar_h), bar)

            # Draw title text
            draw.text(
                (20, img.height - bar_h + 20),
                title[:80],
                font=font,
                fill=(255, 255, 255, 255),
            )

            img.convert("RGB").save(thumb_path, "JPEG", quality=90)
        except Exception as e:
            logger.warning("Thumbnail overlay failed for %s: %s", clip['clip_id'], e)
    elif thumb_path.exists():
        logger.warning("Thumbnail file is 0 bytes for %s", clip['clip_id'])

    return str(thumb_path)