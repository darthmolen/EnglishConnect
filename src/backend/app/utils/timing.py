"""Timing instrumentation for latency analysis.

Usage:
    from app.utils.timing import log_timing, request_id_var

    # At request start
    request_id_var.set(str(uuid.uuid4())[:8])
    log_timing("T1", "request_received")

    # During processing
    log_timing("T2", "llm_start", iteration=1)
    log_timing("T3", "llm_complete", iteration=1, tokens=150)

Output format:
    [TIMING] request_id=abc123 point=T1 ts=1234567890.123 label="request_received"
"""

import logging
import time
from contextvars import ContextVar

# Context variable for request tracking across async calls
request_id_var: ContextVar[str] = ContextVar("request_id", default="unknown")

# Dedicated logger for timing - easy to filter in logs
logger = logging.getLogger("timing")


def log_timing(point: str, label: str, **extra) -> float:
    """Log a timing point with consistent format.

    Args:
        point: Timing point identifier (T1, T2, S1, etc.)
        label: Human-readable label for the timing point
        **extra: Additional key-value pairs to include in log

    Returns:
        The timestamp that was logged (for calculating deltas)
    """
    ts = time.time()
    extra_str = " ".join(f"{k}={v}" for k, v in extra.items())
    logger.info(
        f"[TIMING] request_id={request_id_var.get()} "
        f"point={point} ts={ts:.3f} label={label!r}"
        + (f" {extra_str}" if extra_str else "")
    )
    return ts


def log_timing_delta(point: str, label: str, start_ts: float, **extra) -> float:
    """Log a timing point with delta from a start timestamp.

    Args:
        point: Timing point identifier
        label: Human-readable label
        start_ts: Starting timestamp to calculate delta from
        **extra: Additional key-value pairs

    Returns:
        The current timestamp
    """
    ts = time.time()
    delta_ms = (ts - start_ts) * 1000
    extra_str = " ".join(f"{k}={v}" for k, v in extra.items())
    logger.info(
        f"[TIMING] request_id={request_id_var.get()} "
        f"point={point} ts={ts:.3f} label={label!r} delta_ms={delta_ms:.1f}"
        + (f" {extra_str}" if extra_str else "")
    )
    return ts


class TimingContext:
    """Context manager for timing a block of code.

    Usage:
        with TimingContext("T4", "T5", "tts_call", text_len=45) as ctx:
            result = await some_operation()
        # Automatically logs T4 at start, T5 at end with delta
    """

    def __init__(self, start_point: str, end_point: str, label: str, **extra):
        self.start_point = start_point
        self.end_point = end_point
        self.label = label
        self.extra = extra
        self.start_ts: float = 0
        self.end_ts: float = 0

    def __enter__(self):
        self.start_ts = log_timing(self.start_point, f"{self.label}_start", **self.extra)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_ts = log_timing_delta(
            self.end_point,
            f"{self.label}_complete",
            self.start_ts,
            **self.extra
        )
        return False

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)

    @property
    def delta_ms(self) -> float:
        """Get the elapsed time in milliseconds."""
        return (self.end_ts - self.start_ts) * 1000
