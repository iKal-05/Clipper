"""Pytest fixtures for Clipper API tests."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.services.job_manager import JobManager
from app.services.progress_bus import ProgressBus


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_storage_dir(tmp_path: Path) -> Path:
    """Temporary storage directory for job artifacts."""
    storage = tmp_path / "storage"
    storage.mkdir()
    return storage


@pytest.fixture(autouse=True)
def override_settings(tmp_storage_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Override global settings to use temp storage."""
    settings = Settings(
        storage_dir=tmp_storage_dir,
        jobs_dir=tmp_storage_dir / "jobs",
        cache_dir=tmp_storage_dir / "cache",
        whisper_model_dir=tmp_storage_dir / "models",
    )
    # Reset singletons
    JobManager._instance = None
    ProgressBus._instance = None
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    return settings


@pytest.fixture
def client(override_settings: Settings) -> TestClient:
    """TestClient with overridden settings."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_youtube_url() -> str:
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"