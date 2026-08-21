"""Clip asset endpoints."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import FileResponse

from app.config import get_settings
from app.deps import get_job_manager

router = APIRouter()


@router.get("/clips/{clip_id}/video")
async def get_clip_video(clip_id: str) -> Response:
    """Serve clip video file."""
    settings = get_settings()
    # Find job containing this clip
    for job_dir in settings.jobs_dir.iterdir():
        if not job_dir.is_dir():
            continue
        clip_path = job_dir / "clips" / f"{clip_id}.mp4"
        if clip_path.exists():
            return FileResponse(
                clip_path,
                media_type="video/mp4",
                filename=f"{clip_id}.mp4"
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip video not found")


@router.get("/clips/{clip_id}/thumbnail")
async def get_clip_thumbnail(clip_id: str) -> Response:
    """Serve clip thumbnail."""
    settings = get_settings()
    for job_dir in settings.jobs_dir.iterdir():
        if not job_dir.is_dir():
            continue
        thumb_path = job_dir / "clips" / f"{clip_id}_thumb.jpg"
        if thumb_path.exists():
            return FileResponse(
                thumb_path,
                media_type="image/jpeg",
                filename=f"{clip_id}_thumb.jpg"
            )
    # Return a placeholder SVG
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 1280"><rect fill="#1a1a1a" width="720" height="1280"/></svg>'
    return Response(content=svg, media_type="image/svg+xml")