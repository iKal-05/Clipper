"""End-to-end pipeline stub test."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def test_job_create_and_complete(client: TestClient, sample_youtube_url: str) -> None:
    # Create job
    resp = client.post("/api/jobs", json={"url": sample_youtube_url})
    assert resp.status_code == 201
    job = resp.json()
    job_id = job["id"]
    assert job["status"] == "queued"

    # Poll until done (stub pipeline completes quickly)
    max_wait = 30  # seconds
    start = time.time()
    while time.time() - start < max_wait:
        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        job = resp.json()
        if job["status"] == "done":
            break
        if job["status"] == "error":
            pytest.fail(f"Job failed: {job.get('error')}")
        time.sleep(0.2)
    else:
        pytest.fail(f"Job did not complete within {max_wait}s")

    # Assert final state
    assert job["status"] == "done"
    assert job["pct"] == 100.0
    assert job["clips"] == []
    assert job["error"] is None


def test_job_log_stream(client: TestClient, sample_youtube_url: str) -> None:
    resp = client.post("/api/jobs", json={"url": sample_youtube_url})
    job_id = resp.json()["id"]

    # Wait for completion
    max_wait = 30
    start = time.time()
    while time.time() - start < max_wait:
        r = client.get(f"/api/jobs/{job_id}")
        if r.json()["status"] == "done":
            break
        time.sleep(0.2)

    # Stream log
    resp = client.get(f"/api/jobs/{job_id}/log")
    assert resp.status_code == 200
    lines = resp.text.strip().split("\n")
    assert len(lines) > 0
    # Should have job_created + stage events
    assert any("job_created" in line for line in lines)