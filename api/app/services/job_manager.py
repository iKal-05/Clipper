"""Job lifecycle management with JSONL persistence."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.config import get_settings

logger = logging.getLogger(__name__)


class JobPrefs(BaseModel):
    max_clip_seconds: int = 60
    max_clips: int = 8
    moment_filters: list[str] | None = None
    min_score: float | None = None
    whisper_model: str = "base"
    use_cloud_model: bool = False
    chunk_seconds: int = 300
    overlap_seconds: int = 5


class Job(BaseModel):
    id: str
    url: str
    status: str = "queued"  # queued, downloading, transcribing, analyzing, scoring, cutting, reframing, rendering, assets, done, error
    current_stage: str | None = None
    pct: float = 0.0
    prefs: JobPrefs = Field(default_factory=JobPrefs)
    error: str | None = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    clips: list[str] = Field(default_factory=list)  # clip IDs
    assets: dict[str, Any] = Field(default_factory=dict)  # clip_id -> Asset dict

    def mark_updated(self) -> None:
        self.updated_at = time.time()


class JobManager:
    """In-memory job registry + append-only JSONL log per job."""

    _instance: JobManager | None = None

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._log_files: dict[str, Path] = {}
        self._lock = __import__("asyncio").Lock()

    @classmethod
    def instance(cls) -> JobManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _job_log_path(self, job_id: str) -> Path:
        settings = get_settings()
        return settings.jobs_dir / job_id / "log.jsonl"

    async def create(self, url: str, prefs: JobPrefs | None = None) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, url=url, prefs=prefs or JobPrefs())
        async with self._lock:
            self._jobs[job_id] = job
        # Ensure job dir exists
        log_path = self._job_log_path(job_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_files[job_id] = log_path
        await self._append_log(job_id, {"event": "job_created", "job_id": job_id, "url": url})
        return job

    async def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        current_stage: str | None = None,
        pct: float | None = None,
        error: str | None = None,
        clips: list[str] | None = None,
        assets: dict[str, Any] | None = None,
    ) -> Job | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if status is not None:
                job.status = status
            if current_stage is not None:
                job.current_stage = current_stage
            if pct is not None:
                job.pct = max(0.0, min(100.0, pct))
            if error is not None:
                job.error = error
            if clips is not None:
                job.clips = clips
            if assets is not None:
                job.assets = assets
            job.mark_updated()
        await self._append_log(job_id, {
            "event": "job_updated",
            "status": job.status,
            "stage": job.current_stage,
            "pct": job.pct,
        })
        return job

    async def delete(self, job_id: str) -> bool:
        """Remove job from memory and delete its storage directory."""
        async with self._lock:
            job = self._jobs.pop(job_id, None)
            log_path = self._log_files.pop(job_id, None)
        if job:
            import shutil
            settings = get_settings()
            job_dir = settings.jobs_dir / job_id
            if job_dir.exists():
                shutil.rmtree(job_dir, ignore_errors=True)
            return True
        return False

    async def list(self) -> list[Job]:
        return list(self._jobs.values())

    async def _append_log(self, job_id: str, entry: dict[str, Any]) -> None:
        entry["ts"] = datetime.utcnow().isoformat() + "Z"
        log_path = self._log_files.get(job_id) or self._job_log_path(job_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.warning("Failed to write job log for %s: %s", job_id, e)

    async def stream_log(self, job_id: str) -> AsyncGenerator[str, None]:
        """Yield log lines for SSE/WS streaming."""
        log_path = self._job_log_path(job_id)
        if not log_path.exists():
            return
        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                yield line.rstrip("\n")

    # Convenience typed helpers
    async def start_stage(self, job_id: str, stage: str) -> None:
        await self.update(job_id, status=stage, current_stage=stage, pct=0.0)

    async def progress(self, job_id: str, pct: float) -> None:
        await self.update(job_id, pct=pct)

    async def finish(self, job_id: str, clips: list[str] | None = None) -> None:
        await self.update(job_id, status="done", current_stage=None, pct=100.0, clips=clips)

    async def fail(self, job_id: str, error: str) -> None:
        await self.update(job_id, status="error", error=error)

