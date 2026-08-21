"""Application configuration via pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Storage
    storage_dir: Path = Path("storage")
    jobs_dir: Path = Path("storage/jobs")
    cache_dir: Path = Path("storage/cache")

    # Pipeline defaults
    default_max_clip_seconds: int = 60
    default_max_clips: int = 8
    default_whisper_model: str = "base"
    default_chunk_seconds: int = 300
    default_overlap_seconds: int = 5

    # ffmpeg
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"

    # Whisper model cache
    whisper_model_dir: Path = Path.home() / "AppData" / "Local" / "clipper" / "models"

    # Performance
    max_memory_mb: int = 2048

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure dirs exist
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.whisper_model_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()

