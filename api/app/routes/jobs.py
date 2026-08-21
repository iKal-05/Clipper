"""Job REST endpoints."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from starlette.responses import StreamingResponse
from pydantic import HttpUrl

from app.deps import get_job_manager, get_progress_bus
from app.models.asset import Asset
from app.models.clip import SelectClips
from app.models.job import Job, JobCreate
from app.services.job_manager import JobManager, JobPrefs
from app.services.pipeline_runner import run_pipeline
from app.services.progress_bus import ProgressBus

router = APIRouter()


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    manager=Depends(get_job_manager),
    bus=Depends(get_progress_bus),
):
    job = await manager.create(str(payload.url), payload.to_prefs())
    background_tasks.add_task(_run_pipeline_wrapper, job.id, manager, bus)
    return job


async def _run_pipeline_wrapper(job_id: str, manager: JobManager, bus: ProgressBus) -> None:
    job = await manager.get(job_id)
    if job:
        try:
            await run_pipeline(job)
        except Exception as exc:  # noqa: BLE001
            await manager.fail(job_id, str(exc))
            await bus.error(job_id, str(exc))


@router.get("/jobs/{job_id}", response_model=dict)
async def get_job(job_id: str, manager=Depends(get_job_manager)):
    job = await manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump()


@router.get("/jobs/{job_id}/clips")
async def list_clips(job_id: str, manager=Depends(get_job_manager)):
    job = await manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.config import get_settings
    import json
    settings = get_settings()

    # Read clips.json (written by render stage)
    clips_path = settings.jobs_dir / job_id / "clips.json"
    if not clips_path.exists():
        return []
    clips_data = json.loads(clips_path.read_text(encoding="utf-8"))

    # Read candidates.json for moment labels
    candidates_path = settings.jobs_dir / job_id / "candidates.json"
    candidates = {}
    if candidates_path.exists():
        for c in json.loads(candidates_path.read_text(encoding="utf-8")):
            candidates[c.get("candidate_id", "")] = c

    # Map to frontend Clip interface: id, job_id, start, end, duration, moment_labels, score
    result = []
    for clip in clips_data:
        cid = clip.get("clip_id", "")
        cand = candidates.get(cid, {})
        result.append({
            "id": cid,
            "job_id": job_id,
            "start": clip.get("start", 0),
            "end": clip.get("end", 0),
            "duration": clip.get("duration", 0),
            "score": clip.get("score", 0),
            "moment_labels": [cand.get("label", "Clip")],
            "video_path": clip.get("video_path"),
            "thumbnail_path": None,
        })
    return result


@router.post("/jobs/{job_id}/clips/select", status_code=status.HTTP_202_ACCEPTED)
async def select_clips(
    job_id: str,
    payload: SelectClips,
    manager=Depends(get_job_manager),
):
    job = await manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Save selected clips to storage
    from app.config import get_settings
    import json
    settings = get_settings()
    clips_path = settings.jobs_dir / job_id / "clips.json"
    if clips_path.exists():
        clips_data = json.loads(clips_path.read_text(encoding="utf-8"))
        # Filter to selected clips
        selected = [c for c in clips_data if c["clip_id"] in payload.clip_ids]
        # Apply trims if provided
        if payload.trims:
            for trim in payload.trims:
                for clip in selected:
                    if clip["clip_id"] == trim.clip_id:
                        clip["start"] = trim.start
                        clip["end"] = trim.end
                        clip["duration"] = trim.end - trim.start
        # Save selected clips as "selected_clips.json"
        selected_path = settings.jobs_dir / job_id / "selected_clips.json"
        selected_path.write_text(json.dumps(selected, ensure_ascii=False), encoding="utf-8")

    return {"job_id": job_id, "status": "accepted", "selected_count": len(payload.clip_ids)}


@router.get("/jobs/{job_id}/assets")
async def list_assets(job_id: str, manager=Depends(get_job_manager)):
    job = await manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Read assets.json written by the assets stage
    from app.config import get_settings
    import json
    settings = get_settings()
    assets_path = settings.jobs_dir / job_id / "assets.json"
    if assets_path.exists():
        data = json.loads(assets_path.read_text(encoding="utf-8"))
        return [Asset.model_validate(a) for a in data]
    # Fallback: in-memory job assets (e.g. after restart)
    return [Asset.model_validate(a) for a in job.assets.values()]


@router.get("/jobs/{job_id}/log")
async def stream_log(job_id: str, manager=Depends(get_job_manager)):
    job = await manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def log_generator():
        async for line in manager.stream_log(job_id):
            yield line + "\n"

    return StreamingResponse(log_generator(), media_type="application/x-ndjson")


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, manager=Depends(get_job_manager)):
    ok = await manager.delete(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/jobs/{job_id}/cleanup", status_code=status.HTTP_204_NO_CONTENT)
async def cleanup_job(job_id: str, manager=Depends(get_job_manager)):
    """Delete job storage but keep job record (for history)."""
    from app.services.cleanup import purge_job
    ok = purge_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job storage not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)