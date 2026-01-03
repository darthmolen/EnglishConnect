# Latency Analysis Report

**Date**: 2026-01-03
**Status**: Complete - Optimization Deferred

## Executive Summary

Latency instrumentation was added across the full pipeline (Frontend → Backend → TTS/STT) to identify bottlenecks before implementing MCP streaming. **Key finding: TTS synthesis accounts for 70-90% of total latency. Network overhead is negligible (<50ms). MCP streaming would not help.**

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  TTS (GPU)  │
│   (React)   │◀────│  (FastAPI)  │◀────│  VibeVoice  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       │                   ▼
       │            ┌─────────────┐
       └───────────▶│  STT (GPU)  │
                    │   Whisper   │
                    └─────────────┘
```

### Components

| Component | Technology | Port |
| --------- | ---------- | ---- |
| Frontend | React + Vite | 5173 |
| Backend | FastAPI | 8000 |
| TTS | VibeVoice-Realtime-0.5B | 8002 |
| STT | faster-whisper (medium) | 8001 |
| LLM | Azure GPT-4o-mini | - |

## Instrumentation Points

### TTS Pipeline (T0-T11)

| Point | Location | Description |
| ----- | -------- | ----------- |
| T0 | Frontend | Request sent |
| T1 | Backend | Request received |
| T2 | Backend | LLM iteration start |
| T3 | Backend | LLM iteration complete |
| T4 | Backend | Tool call start (speak) |
| T5 | Backend | Tool call complete |
| T6 | TTS | Synthesis start |
| T7 | TTS | Inference start |
| T8 | TTS | Synthesis complete |
| T9 | Backend | Response sent |
| T10 | Frontend | Response received |
| T11 | Frontend | Audio playback starts |

### STT Pipeline (S0-S5)

| Point | Location | Description |
| ----- | -------- | ----------- |
| S0 | Frontend | Recording starts |
| S1 | Frontend | Audio sent to STT |
| S2 | STT | Request received |
| S3 | STT | Transcription start |
| S4 | STT | Transcription complete |
| S5 | Frontend | Result received |

## Test Results

### STT Performance

| Metric | Avg | Min | Max |
| ------ | --- | --- | --- |
| Transcription (S1→S5) | 562ms | 227ms | 2746ms |
| Recording time | 3.2-5.7s | - | - |

**Verdict**: STT is fast. No optimization needed.

### TTS Performance

| Metric | Avg | Min | Max |
| ------ | --- | --- | --- |
| Backend total (T0→T10) | 6128ms | 2899ms | 12455ms |
| Playback start (T0→T11) | 6740ms | 2931ms | 20131ms |
| Decode overhead (T10→T11) | ~40ms | - | - |

### Bottleneck Breakdown

| Component | Time Range | % of Total |
| --------- | ---------- | ---------- |
| LLM per iteration | 500-1800ms | 10-25% |
| **TTS synthesis** | 869-10496ms | **70-90%** |
| Network overhead | ~20-40ms | <1% |

### TTS Scales with Text Length

| Text Length | TTS Time |
| ----------- | -------- |
| 42 chars | 869ms |
| 87 chars | 2400ms |
| 132 chars | 4331ms |
| 238 chars | 6428ms |
| 272 chars | 10496ms |

**Rate**: ~38ms per character at 24kHz

## Conclusions

1. **TTS synthesis is THE bottleneck** (70-90% of latency)
2. **Network overhead is negligible** (<50ms)
3. **MCP streaming won't help** - synthesis must complete before sending
4. **STT is already fast** (300-600ms typical)

## Recommendations (Deferred)

### High Impact

1. **Shorter agent responses** - Keep speak() calls under 100 chars
2. **Sentence-by-sentence TTS** - Stream audio as sentences complete

### Medium Impact

3. **Keep TTS as HTTP** - No benefit from MCP for audio
4. **Use MCP for STT** - For cloud backend swappability

See `planning/backlog/latency-optimization.md` for detailed optimization plan.

## Raw Data Location

- Backend logs: `logs/backend-20260103-111717.log`
- TTS logs: `logs/tts-20260103-111717.log`
- Frontend console: `tests/log_samples/timing_console.log`

## Instrumentation Code

Timing instrumentation remains in place for future analysis:

- `src/backend/app/utils/timing.py` - Backend timing utility
- `src/backend/app/routers/timing.py` - Frontend log aggregation endpoint
- `src/frontend/src/utils/timing.ts` - Frontend timing utility
- `src/services/tts-mcp/server.py` - TTS timing (T6, T7, T8)
- `src/services/stt/server.py` - STT timing (S2, S3, S4)
