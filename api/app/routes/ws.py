"""WebSocket progress stream."""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from app.deps import get_job_manager, get_progress_bus

router = APIRouter()


@router.websocket("/jobs/{job_id}/stream")
async def job_stream(
    websocket: WebSocket,
    job_id: str,
    manager=Depends(get_job_manager),
    bus=Depends(get_progress_bus),
) -> None:
    # Validate job exists
    job = await manager.get(job_id)
    if not job:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Job not found")
        return

    await websocket.accept()
    queue = await bus.subscribe(job_id)
    try:
        # Send current status immediately
        await websocket.send_json({
            "type": "stage",
            "stage": job.current_stage or job.status,
            "status": "started" if job.status not in ("done", "error") else "finished",
            "pct": job.pct,
        })
        # Forward events
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("type") in ("done", "error"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        await bus.unsubscribe(job_id, queue)