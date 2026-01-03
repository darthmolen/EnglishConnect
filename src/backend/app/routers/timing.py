"""Timing log aggregation endpoint.

Frontend POSTs timing events here so all timing logs end up in one place.
"""

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/timing", tags=["timing"])

# Use the same timing logger as the rest of the backend
timing_logger = logging.getLogger("timing")


class TimingEvent(BaseModel):
    """A timing event from the frontend."""

    request_id: str
    point: str
    ts: float
    label: str
    extra: Optional[dict] = None


class TimingBatch(BaseModel):
    """Batch of timing events."""

    events: list[TimingEvent]


@router.post("/log")
async def log_timing_event(event: TimingEvent):
    """Log a single timing event from frontend."""
    extra_str = ""
    if event.extra:
        extra_str = " " + " ".join(f"{k}={v}" for k, v in event.extra.items())

    timing_logger.info(
        f"[TIMING] request_id={event.request_id} "
        f"point={event.point} ts={event.ts:.3f} label={event.label!r}"
        f"{extra_str} source=frontend"
    )
    return {"status": "ok"}


@router.post("/batch")
async def log_timing_batch(batch: TimingBatch):
    """Log a batch of timing events from frontend."""
    for event in batch.events:
        extra_str = ""
        if event.extra:
            extra_str = " " + " ".join(f"{k}={v}" for k, v in event.extra.items())

        timing_logger.info(
            f"[TIMING] request_id={event.request_id} "
            f"point={event.point} ts={event.ts:.3f} label={event.label!r}"
            f"{extra_str} source=frontend"
        )
    return {"status": "ok", "count": len(batch.events)}
