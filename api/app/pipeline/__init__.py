"""Pipeline stage registry.

Stages are async callables `async def run(ctx: StageContext) -> Any`. They are
registered in declaration order. Real implementations land in M4-M9; this
module ships stubs so the end-to-end pipeline can run without optional deps.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.services.pipeline_runner import StageContext, StageFn, register_stage

logger = logging.getLogger(__name__)


@dataclass
class StageInfo:
    name: str  # identifier used in Job.status
    fn: StageFn


def _stub(label: str) -> Callable[[StageContext], Awaitable[None]]:
    async def run(ctx: StageContext) -> None:
        await ctx.log("info", f"{label} (stub) running")
        await ctx.progress_cb(0.5, f"{label} (stub)")
        await ctx.progress_cb(1.0)

    return run


STUB_STAGES: list[tuple[str, Callable[[StageContext], Awaitable[None]]]] = [
    ("downloading", _stub("download")),
    ("transcribing", _stub("transcribe")),
    ("analyzing", _stub("analyze")),
    ("scoring", _stub("score")),
    ("cutting", _stub("cut")),
    ("reframing", _stub("reframe")),
    ("rendering", _stub("render")),
    ("subtitle", _stub("subtitle")),
    ("assets", _stub("assets")),
]


def register_default_stages() -> None:
    """Register pipeline. Real stages replace stubs as milestones progress."""
    from app.services.pipeline_runner import STAGES

    existing = {name for name, _ in STAGES}

    # M4 download
    if "downloading" not in existing:
        from app.pipeline.download import run as download_run
        register_stage("downloading", download_run)

    # M5 transcribe
    if "transcribing" not in existing:
        from app.pipeline.transcribe import run as transcribe_run
        register_stage("transcribing", transcribe_run)

    # M6 analyze & score
    if "analyzing" not in existing:
        from app.pipeline.analyze import run as analyze_run
        register_stage("analyzing", analyze_run)
    if "scoring" not in existing:
        from app.pipeline.score import run as score_run
        register_stage("scoring", score_run)

    # M7 cut, reframe, render
    if "cutting" not in existing:
        from app.pipeline.cut import run as cut_run
        register_stage("cutting", cut_run)
    if "reframing" not in existing:
        from app.pipeline.reframe import run as reframe_run
        register_stage("reframing", reframe_run)
    if "rendering" not in existing:
        from app.pipeline.render import run as render_run
        register_stage("rendering", render_run)

    # M8 subtitle
    if "subtitle" not in existing:
        from app.pipeline.subtitle import run as subtitle_run
        register_stage("subtitle", subtitle_run)

    # M9 assets
    if "assets" not in existing:
        from app.pipeline.assets import run as assets_run
        register_stage("assets", assets_run)

    # remaining stubs
    for name, fn in STUB_STAGES:
        if name not in existing and name not in ("downloading", "transcribing", "analyzing", "scoring", "cutting", "reframing", "rendering", "subtitle", "assets"):
            register_stage(name, fn)


__all__ = ["StageContext", "StageFn", "StageInfo", "register_default_stages", "STUB_STAGES"]