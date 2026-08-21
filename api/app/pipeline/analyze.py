"""Analyze stage: visual + audio feature extraction (with graceful fallbacks)."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from app.services.pipeline_runner import StageContext

logger = logging.getLogger(__name__)


async def run(ctx: StageContext) -> dict[str, Any]:
    """Extract visual and audio features. Write analysis.json to storage_dir."""
    storage = Path(ctx.storage_dir)
    video_path = storage / "source.mp4"
    audio_path = storage / "audio.wav"

    # Visual analysis in chunks
    visual = await _analyze_visual(video_path, ctx)
    # Audio analysis
    audio = await _analyze_audio(audio_path, ctx)

    analysis = {
        "visual": visual,
        "audio": audio,
    }
    out_path = storage / "analysis.json"
    await asyncio.to_thread(out_path.write_text, json.dumps(analysis))
    await ctx.progress_cb(1.0, "Analysis complete")
    return analysis


async def _analyze_visual(video_path: Path, ctx: StageContext) -> dict[str, Any]:
    """CV2 frame diff + motion + face tracks (MediaPipe if available)."""
    # Try to import cv2
    try:
        import cv2
    except Exception:
        logger.warning("OpenCV not available, returning empty visual analysis")
        return {"chunks": [], "face_tracks": [], "duration": 0, "fps": 0, "width": 0, "height": 0}

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {"chunks": [], "face_tracks": [], "duration": 0, "fps": 0, "width": 0, "height": 0}

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    chunk_sec = ctx.prefs.chunk_seconds
    overlap_sec = ctx.prefs.overlap_seconds
    chunk_frames = int(chunk_sec * fps)
    overlap_frames = int(overlap_sec * fps)

    chunks = []
    face_tracks = []

    # Try to import mediapipe
    has_mp = False
    try:
        import mediapipe as mp
        face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)
        has_mp = True
    except Exception:
        logger.info("MediaPipe not available, skipping face detection")

    prev_gray = None
    frame_idx = 0
    chunk_idx = 0
    # Accumulate motion scores within current chunk for a true average
    chunk_motion_sum = 0.0
    chunk_motion_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        motion_score = 0.0
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            motion_score = float(diff.mean() / 255.0)
            chunk_motion_sum += motion_score
            chunk_motion_count += 1

        # Face detection per chunk (sample 1 fps)
        if has_mp and frame_idx % int(fps) == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            if results.multi_face_landmarks:
                lm = results.multi_face_landmarks[0].landmark
                # nose tip = landmark 1
                nose = lm[1]
                face_tracks.append({
                    "frame": frame_idx,
                    "time": frame_idx / fps,
                    "x": nose.x,
                    "y": nose.y,
                })

        prev_gray = gray
        frame_idx += 1

        # Chunk boundary
        if frame_idx % chunk_frames == 0 or frame_idx == total_frames:
            chunk_end = frame_idx
            chunk_start = max(0, chunk_end - chunk_frames)
            motion_avg = chunk_motion_sum / chunk_motion_count if chunk_motion_count else 0.0
            chunks.append({
                "start": chunk_start / fps,
                "end": chunk_end / fps,
                "motion_avg": motion_avg,
            })
            chunk_idx += 1
            chunk_motion_sum = 0.0
            chunk_motion_count = 0
            await ctx.progress_cb(min(frame_idx / total_frames, 0.9), f"Visual chunk {chunk_idx}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    if has_mp:
        face_mesh.close()

    return {"chunks": chunks, "face_tracks": face_tracks, "duration": duration, "fps": fps, "width": width, "height": height}


async def _analyze_audio(audio_path: Path, ctx: StageContext) -> dict[str, Any]:
    """Audio analysis: energy, pitch, laughter detection."""
    # Try to import scipy/numpy
    try:
        import numpy as np
        from scipy.io import wavfile
        from scipy.signal import find_peaks
    except Exception:
        logger.warning("SciPy/NumPy not available, returning empty audio analysis")
        return {"energy": [], "pitch": [], "laughter_peaks": []}

    if not audio_path.exists():
        return {"energy": [], "pitch": [], "laughter_peaks": []}

    sr, data = await asyncio.to_thread(wavfile.read, str(audio_path))
    if data.ndim > 1:
        data = data.mean(axis=1)
    data = data.astype(np.float32) / 32768.0

    # Energy in 100ms windows
    win = int(sr * 0.1)
    energy = []
    for i in range(0, len(data), win):
        chunk = data[i:i+win]
        if len(chunk) > 0:
            energy.append(float(np.sqrt(np.mean(chunk**2))))

    # Pitch via autocorrelation (simplified)
    pitch = []
    for i in range(0, len(data), win):
        chunk = data[i:i+win]
        if len(chunk) >= 128:
            corr = np.correlate(chunk, chunk, mode="full")
            corr = corr[len(corr)//2:]
            peaks, _ = find_peaks(corr[1:], distance=20)
            if len(peaks) > 0:
                pitch.append(float(sr / (peaks[0] + 1)))
            else:
                pitch.append(0.0)

    # Laughter detection: high-frequency energy bursts
    laughter = []
    if len(energy) > 10:
        high_freq_energy = np.array(energy)
        peaks, _ = find_peaks(high_freq_energy, height=np.percentile(high_freq_energy, 90), distance=10)
        laughter = [float(i * 0.1) for i in peaks]

    return {
        "energy": energy,
        "pitch": pitch,
        "laughter_peaks": laughter,
    }