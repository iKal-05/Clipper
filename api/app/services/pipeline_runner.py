"""Pipeline runner: orchestrates stage execution with progress, retries, and error handling."""

from __future__ import annotations

import asyncio
import gc
import logging
import time
from dataclasses import dataclass
from typing import Any
from collections.abc import Awaitable, Callable

from app.config import get_settings
from app.services.job_manager import Job, JobManager
from app.services.progress_bus import ProgressBus

logger = logging.getLogger(__name__)


@dataclass
class StageContext:
    job_id: str
    url: str
    storage_dir: str
    prefs: Any
    progress_cb: Callable[[float, str | None], Awaitable[None]]
    log: Callable[[str, str], Awaitable[None]]


StageFn = Callable[[StageContext], Awaitable[Any]]

# Ordered pipeline stages. Identifier -> (stage_name, callable).
# Stages registered in app.pipeline.__init__; here we keep a registry populated lazily.
STAGES: list[tuple[str, StageFn]] = []


def register_stage(stage_id: str, fn: StageFn) -> None:
    STAGES.append((stage_id, fn))


MAX_RETRIES = 2
RETRY_DELAY = 5  # seconds


async def run_pipeline(job: Job) -> None:
    """Execute all stages for a job, emitting progress via ProgressBus + JobManager."""
    manager = JobManager.instance()
    bus = ProgressBus.instance()
    settings = get_settings()
    storage_dir = str(settings.jobs_dir / job.id)

    async def progress_cb(pct: float, msg: str | None = None) -> None:
        await manager.progress(job.id, pct)
        if msg:
            await bus.log(job.id, "info", msg)

    async def log_fn(level: str, msg: str) -> None:
        await bus.log(job.id, level, msg)

    ctx = StageContext(
        job_id=job.id,
        url=job.url,
        storage_dir=storage_dir,
        prefs=job.prefs,
        progress_cb=progress_cb,
        log=log_fn,
    )

    total = len(STAGES) or 1
    try:
        for idx, (stage_id, fn) in enumerate(STAGES):
            # Memory check before each stage
            await _check_memory(settings, job.id, bus)

            await manager.start_stage(job.id, stage_id)
            await bus.stage(job.id, stage_id, "started", pct=idx / total * 100)
            await ctx.log("info", f"{stage_id} started")

            # Execute with retries
            last_exc = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    await fn(ctx)
                    break  # success
                except Exception as exc:
                    last_exc = exc
                    if attempt < MAX_RETRIES:
                        await ctx.log("warn", f"{stage_id} attempt {attempt + 1} failed: {exc}. Retrying in {RETRY_DELAY}s...")
                        await asyncio.sleep(RETRY_DELAY)
                        # Force GC before retry
                        gc.collect()
                    else:
                        await ctx.log("error", f"{stage_id} failed after {MAX_RETRIES + 1} attempts: {exc}")
                        raise

            await bus.stage(job.id, stage_id, "finished", pct=(idx + 1) / total * 100)
            await ctx.log("info", f"{stage_id} finished")

            # Force GC between stages to bound memory
            gc.collect()

        await manager.finish(job.id)
        await bus.done(job.id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed for job %s", job.id)
        await manager.fail(job.id, str(exc))
        await bus.error(job.id, str(exc))


async def _check_memory(settings: Any, job_id: str, bus: ProgressBus) -> None:
    """Check RSS and warn if approaching limit."""
    try:
        import psutil
        process = psutil.Process()
        rss_mb = process.memory_info().rss / 1024 / 1024
        if rss_mb > settings.max_memory_mb * 0.85:
            await bus.log(job_id, "warn", f"High memory usage: {rss_mb:.0f} MB ({rss_mb / settings.max_memory_mb * 100:.0f}% of limit)")
    except Exception:
        pass  # psutil not available or error