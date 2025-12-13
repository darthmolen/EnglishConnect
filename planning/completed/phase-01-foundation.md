# Phase 1: Foundation + Local Voice Stack

**Status**: ✅ Complete

## Completed Tasks

- [x] Set up VibeVoice-Realtime-0.5B on local 5090 GPU
- [x] Create TTS MCP server (`services/tts-mcp/server.py`)
- [x] Test TTS streaming - RTF 0.51x achieved (real-time capable)
- [x] Set up faster-whisper STT service (`services/stt/server.py`)
- [x] Configure WSL audio (PulseAudio via ALSA bridge)
- [x] Create Docker infrastructure (postgres, redis in docker-compose.yml)

## Key Files Created

| File | Purpose |
|------|---------|
| `services/tts-mcp/server.py` | VibeVoice MCP server with `speak()` tool |
| `services/tts-mcp/test_streaming_playback.py` | TTS streaming test harness |
| `services/stt/server.py` | faster-whisper HTTP/WebSocket API |
| `services/stt/Dockerfile` | CUDA container for STT |

## Performance Metrics (TTS)

- **RTF**: 0.51x (real-time capable)
- **First chunk latency**: ~300ms
- **Sample rate**: 24kHz
- **Voices**: 6 English speakers (Carter, Emma, Davis, Grace, Frank, Mike)

## WSL Audio Setup

Fixed by creating `~/.asoundrc` to bridge ALSA to PulseAudio:
```
pcm.pulse { type pulse }
ctl.pulse { type pulse }
pcm.!default { type pulse }
ctl.!default { type pulse }
```
