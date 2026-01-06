# Backlog: TTS Streaming Investigation

**Priority**: Low
**Dependencies**: None (optimization)
**Related**: Phase 12 cloud deployment

## Context

When agent responds in multiple languages (Spanish + English), TTS generates full WAV files sequentially. Current implementation waits for all TTS calls to complete before playing first audio.

## Opportunity

VibeVoice uses `VibeVoiceStreamingForConditionalGenerationInference` which supports streaming inference. Streaming would:
- Reduce time to first audio (user hears first words while rest generates)
- More natural conversation pacing
- Lower perceived latency

## Investigation Needed

1. Can VibeVoice streaming be exposed via WebSocket or SSE?
2. How to stream audio chunks to frontend incrementally?
3. Frontend changes to play audio as chunks arrive
4. Latency measurements to validate improvement

## Current State

Queue-based playback works. Streaming is an optimization, not a fix.
