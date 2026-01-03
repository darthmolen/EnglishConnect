# Latency Optimization Plan

**Status**: Backlog (Deferred 2026-01-03)
**Priority**: Medium
**Prerequisite**: Complete functional testing and deployment

## Context

Latency analysis (see `documentation/latency-analysis-2026-01-03.md`) identified TTS synthesis as the primary bottleneck (70-90% of total latency). Network overhead is negligible, so MCP streaming is not the solution.

## Problem Statement

- Current end-to-end latency: 3-12 seconds depending on response length
- TTS synthesis scales linearly: ~38ms per character
- Long responses (272 chars) take 10+ seconds just for audio generation
- User perceives significant delay between speaking and hearing response

## Proposed Solutions

### Solution 1: Shorter Agent Responses (Recommended First)

**Effort**: Low
**Impact**: High

Modify agent prompts to generate shorter responses:

- Target: <100 characters per speak() call
- Expected improvement: 10s → 3s for typical response
- No code changes required, only prompt engineering

Files to modify:

- `src/backend/app/prompts/agent/base.md`
- `src/backend/app/prompts/agent/mode_practice.md`
- `src/backend/app/prompts/agent/mode_help.md`

### Solution 2: Sentence-by-Sentence TTS Streaming

**Effort**: Medium-High
**Impact**: High

Split text into sentences and synthesize each separately:

1. Agent generates full response text
2. Backend splits into sentences
3. First sentence synthesized immediately
4. Subsequent sentences synthesized in parallel/sequentially
5. Audio chunks streamed to frontend as they complete

Benefits:

- First audio starts in ~1s instead of waiting for full response
- User hears beginning while rest is generating
- Perceived latency dramatically reduced

Implementation approach:

- Add sentence splitting in backend tool handler
- Modify frontend to handle multiple audio chunks
- Consider WebSocket for streaming delivery
- Handle audio chunk concatenation/playback

### Solution 3: MCP Abstraction for STT (Cloud Migration)

**Effort**: Medium
**Impact**: Low (latency), High (maintainability)

Wrap STT service in MCP for backend swappability:

- Accept ~50-100ms overhead for abstraction
- Enables Azure → other cloud migration
- Already has WebSocket streaming capability

This is primarily for architectural consistency, not latency improvement.

## Non-Solutions

### MCP Streaming for TTS

Rejected because:

- Synthesis must complete before any audio can be sent
- `report_progress()` adds overhead without benefit
- Network is not the bottleneck (<50ms overhead)

### Faster TTS Model

VibeVoice-Realtime-0.5B is already optimized for real-time synthesis. Faster models typically sacrifice quality.

## Implementation Order

1. **Phase 1**: Shorter responses (prompt engineering) - No code changes
2. **Phase 2**: Evaluate if sufficient, measure new latency
3. **Phase 3**: If still needed, implement sentence-by-sentence streaming
4. **Phase 4**: Consider MCP for STT when preparing cloud deployment

## Acceptance Criteria

- Typical response latency under 3 seconds (T0→T11)
- First audio byte within 1.5 seconds for streaming solution
- No degradation in audio quality or conversation flow

## Related Documents

- `documentation/latency-analysis-2026-01-03.md` - Analysis results
- `logs/backend-20260103-111717.log` - Raw timing data
- `logs/tts-20260103-111717.log` - TTS service logs
- `tests/log_samples/timing_console.log` - Frontend timing data
