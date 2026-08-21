"""Storage cleanup utilities."""

from __future__ import annotations

import logging
import shutil

from app.config import get_settings

logger = logging.getLogger(__name__)


def purge_job(job_id: str) -> bool:
    """Delete a job's storage directory."""
    settings = get_settings()
    job_dir = settings.jobs_dir / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
        return True
    return False


def purge_all() -> int:
    """Wipe all job storage. Returns number of jobs removed."""
    settings = get_settings()
    if not settings.jobs_dir.exists():
        return 0
    removed = 0
    for entry in settings.jobs_dir.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
    return removed


def purge_cache() -> int:
    """Wipe cache directory. M11 will add RAM-aware cache eviction."""
    settings = get_settings()
    if not settings.cache_dir.exists():
        return 0
    n = 0
    for entry in settings.cache_dir.iterdir():
        shutil.rmtree(entry, ignore_errors=True)
        n += 1
    return n
