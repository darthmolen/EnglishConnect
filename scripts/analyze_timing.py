#!/usr/bin/env python3
"""Analyze timing logs to find latency bottlenecks.

Usage:
    # Parse from file
    python analyze_timing.py timing.log

    # Parse from stdin (pipe from service logs)
    grep "\\[TIMING\\]" backend.log | python analyze_timing.py
"""

import re
import sys
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class TimingEvent:
    request_id: str
    point: str
    ts: float
    label: str
    extra: dict


def parse_timing_line(line: str) -> TimingEvent | None:
    """Parse a timing log line."""
    match = re.search(
        r'\[TIMING\]\s+request_id=(\S+)\s+point=(\S+)\s+ts=([\d.]+)\s+label=["\']([^"\']+)["\'](.*)$',
        line
    )
    if not match:
        return None

    request_id, point, ts, label, extra_str = match.groups()

    # Parse extra key=value pairs
    extra = {}
    for kv in re.findall(r'(\w+)=(\S+)', extra_str):
        key, value = kv
        try:
            extra[key] = float(value)
        except ValueError:
            extra[key] = value

    return TimingEvent(
        request_id=request_id,
        point=point,
        ts=float(ts),
        label=label,
        extra=extra
    )


def analyze_request(events: list[TimingEvent]) -> dict:
    """Analyze timing events for a single request."""
    events_by_point = {e.point: e for e in events}

    analysis = {
        "request_id": events[0].request_id,
        "points_captured": list(events_by_point.keys()),
    }

    # TTS pipeline analysis
    if "T0" in events_by_point and "T11" in events_by_point:
        analysis["total_perceived_latency_ms"] = (
            events_by_point["T11"].ts - events_by_point["T0"].ts
        ) * 1000

    if "T0" in events_by_point and "T10" in events_by_point:
        analysis["network_round_trip_ms"] = (
            events_by_point["T10"].ts - events_by_point["T0"].ts
        ) * 1000

    if "T1" in events_by_point and "T9" in events_by_point:
        analysis["backend_processing_ms"] = (
            events_by_point["T9"].ts - events_by_point["T1"].ts
        ) * 1000

    if "T2" in events_by_point and "T3" in events_by_point:
        analysis["llm_latency_ms"] = (
            events_by_point["T3"].ts - events_by_point["T2"].ts
        ) * 1000

    if "T4" in events_by_point and "T5" in events_by_point:
        analysis["tts_call_latency_ms"] = (
            events_by_point["T5"].ts - events_by_point["T4"].ts
        ) * 1000

    if "T6" in events_by_point and "T8" in events_by_point:
        analysis["tts_synthesis_ms"] = (
            events_by_point["T8"].ts - events_by_point["T6"].ts
        ) * 1000

    # Network overhead for TTS (call latency - synthesis)
    if "tts_call_latency_ms" in analysis and "tts_synthesis_ms" in analysis:
        analysis["tts_network_overhead_ms"] = (
            analysis["tts_call_latency_ms"] - analysis["tts_synthesis_ms"]
        )

    # STT pipeline analysis
    if "S0" in events_by_point and "S5" in events_by_point:
        analysis["stt_total_latency_ms"] = (
            events_by_point["S5"].ts - events_by_point["S0"].ts
        ) * 1000

    if "S1" in events_by_point and "S5" in events_by_point:
        analysis["stt_transcription_round_trip_ms"] = (
            events_by_point["S5"].ts - events_by_point["S1"].ts
        ) * 1000

    if "S3" in events_by_point and "S4" in events_by_point:
        analysis["stt_whisper_inference_ms"] = (
            events_by_point["S4"].ts - events_by_point["S3"].ts
        ) * 1000

    return analysis


def main():
    # Read from file or stdin
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.readlines()

    # Parse all timing events
    events_by_request = defaultdict(list)
    for line in lines:
        event = parse_timing_line(line)
        if event:
            events_by_request[event.request_id].append(event)

    if not events_by_request:
        print("No timing events found.")
        return

    print(f"Found {len(events_by_request)} requests with timing data\n")

    # Analyze each request
    all_analyses = []
    for request_id, events in sorted(events_by_request.items(), key=lambda x: x[1][0].ts):
        events.sort(key=lambda e: e.ts)
        analysis = analyze_request(events)
        all_analyses.append(analysis)

        print(f"=== Request {analysis['request_id']} ===")
        print(f"Points captured: {', '.join(analysis['points_captured'])}")

        for key, value in analysis.items():
            if key.endswith("_ms"):
                print(f"  {key}: {value:.1f}ms")
        print()

    # Summary statistics
    if len(all_analyses) > 1:
        print("=== SUMMARY ===")

        metrics = [
            "total_perceived_latency_ms",
            "backend_processing_ms",
            "llm_latency_ms",
            "tts_call_latency_ms",
            "tts_synthesis_ms",
            "tts_network_overhead_ms",
            "stt_total_latency_ms",
            "stt_whisper_inference_ms",
        ]

        for metric in metrics:
            values = [a[metric] for a in all_analyses if metric in a]
            if values:
                avg = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)
                print(f"{metric}:")
                print(f"  avg={avg:.1f}ms  min={min_val:.1f}ms  max={max_val:.1f}ms  n={len(values)}")


if __name__ == "__main__":
    main()
