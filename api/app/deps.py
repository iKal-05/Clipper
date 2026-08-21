"""FastAPI dependency helpers."""

from collections.abc import AsyncGenerator

from app.config import Settings, get_settings
from app.services.job_manager import JobManager
from app.services.progress_bus import ProgressBus


def get_job_manager() -> JobManager:
    """Singleton-ish access; JobManager manages its own lifecycle."""
    return JobManager.instance()


def get_progress_bus() -> ProgressBus:
    return ProgressBus.instance()


def get_app_settings() -> Settings:
    return get_settings()


async def get_settings_dep() -> AsyncGenerator[Settings, None]:
    yield get_settings()
