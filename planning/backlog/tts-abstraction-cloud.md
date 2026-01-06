# Backlog: TTS Abstraction & Cloud Migration

**Priority**: Medium
**Dependencies**: Phase 12 infrastructure decisions
**Related**: Azure cloud deployment, vocab audio quality

## Context

Currently using VibeVoice (local GPU) for agent TTS and Piper (local CPU) for static vocabulary audio. Neither is deployable to cloud without significant infrastructure.

## Goal

Create abstraction layer enabling seamless switch between local and cloud TTS providers.

## Target Provider

`gpt-4o-mini-tts` (Azure AI Foundry):
- 70% cheaper than gpt-realtime
- 35% fewer word errors in multilingual
- Native Spanish and English support
- HD voice quality with emotion detection

## Implementation Steps

1. Create `TTSProvider` interface with `synthesize(text, language, voice_style)`
2. Implement `VibeVoiceTTS` (current local provider)
3. Implement `AzureTTS` using gpt-4o-mini-tts API
4. Add provider selection via environment config (`TTS_PROVIDER=vibevoice|azure`)
5. Test bilingual quality parity with current Piper static audio

## Cloud Migration Options

### Option A: Component-by-Component Migration

Replace each local service with cloud equivalent:

| Component | Cloud Alternative | Notes |
|-----------|-------------------|-------|
| STT | `gpt-4o-mini-transcribe` | Azure AI Foundry |
| TTS | `gpt-4o-mini-tts` | Azure AI Foundry |
| LLM | `gpt-4o-mini` | Already using |

**Pros**: Minimal architecture change, same data flow
**Cons**: Multiple API calls, higher latency

### Option B: Azure Realtime API (Recommended for Cloud)

Replace entire voice pipeline with single WebSocket:

| Model | Capability |
|-------|------------|
| `gpt-4o-mini-realtime-preview` | STT + LLM + TTS in one connection |

**Features**:
- Single WebSocket handles entire conversation
- Built-in VAD (no separate service needed)
- Sub-second latency (~500ms)
- Natural interruption handling
- Streaming audio input/output

**Pros**: Simpler architecture, lower latency, less infrastructure
**Cons**: Per-minute billing, less voice customization, audio leaves device

### Option C: Hybrid

- Keep local STT/TTS for development and low-cost testing
- Use Realtime API for production
- Feature flag to switch between modes

## Timing

After customer cloud provider preferences are known, before Phase 12 cloud deployment.
