"""In-memory pub/sub for job progress events (WebSocket fan-out)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ProgressBus:
    """Per-job set of subscriber queues. Broadcast ProgressEvent dicts."""

    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    _instance: ProgressBus | None = None

    @classmethod
    def instance(cls) -> ProgressBus:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subs.setdefault(job_id, set()).add(queue)
        return queue

    async def unsubscribe(self, job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            subs = self._subs.get(job_id)
            if subs and queue in subs:
                subs.discard(queue)
                if not subs:
                    self._subs.pop(job_id, None)

    async def publish(self, job_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            subs = list(self._subs.get(job_id, set()))
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("progress queue full for job %s, dropping event", job_id)

    # Convenience typed emitters
    async def stage(
        self, job_id: str, stage: str, status: str, pct: float
    ) -> None:
        await self.publish(
            job_id, {"type": "stage", "stage": stage, "status": status, "pct": round(pct, 2)}
        )

    async def log(self, job_id: str, level: str, msg: str) -> None:
        await self.publish(job_id, {"type": "log", "level": level, "msg": msg})

    async def clips_ready(self, job_id: str, count: int) -> None:
        await self.publish(job_id, {"type": "clips_ready", "count": count})

    async def done(self, job_id: str) -> None:
        await self.publish(job_id, {"type": "done"})

    async def error(self, job_id: str, message: str) -> None:
        await self.publish(job_id, {"type": "error", "message": message})
