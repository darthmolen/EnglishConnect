# Local TTS Voice Service

EnglishConnect uses **VibeVoice-Realtime-0.5B** for local text-to-speech synthesis. This runs entirely on GPU without external API calls, providing low-latency voice generation.

## Overview

| Property | Value |
|----------|-------|
| Model | microsoft/VibeVoice-Realtime-0.5B |
| Sample Rate | 24000 Hz |
| Output Format | WAV (float32) |
| Device | CUDA (GPU required) |
| HTTP Port | 8002 |

## Available Voices

| Voice ID | Name | Gender | Description |
|----------|------|--------|-------------|
| `speaker_a` | Carter | Male | Clear, professional |
| `speaker_b` | Emma | Female | Warm, friendly (more upbeat) |
| `speaker_c` | Davis | Male | Conversational |
| `speaker_d` | Grace | Female | Clear, articulate |
| `speaker_e` | Frank | Male | Authoritative |
| `speaker_f` | Mike | Male | Casual, friendly |

### Default Voices for Demo Audio

| Role | Voice ID | Name |
|------|----------|------|
| Teacher | `speaker_d` | Grace |
| Student | `speaker_c` | Davis |

## Managing the TTS Server

### Slash Commands (Claude Code)

```
/start-tts    Start the TTS server in HTTP mode
/stop-tts     Stop the TTS server
```

### Manual Commands

**Start the server:**
```bash
cd src/services/tts-mcp
source .venv/bin/activate
python server.py --http
```

**Stop the server:**
```bash
pkill -f "python server.py --http"
```

**Verify it's running:**
```bash
curl http://localhost:8002/health
```

## Previewing Voices

### Quick Test

Use the streaming playback test script:

```bash
cd src/services/tts-mcp
source .venv/bin/activate

# Test with default voice (Carter)
python test_streaming_playback.py --text "Hello, how are you today?"

# Test specific voice
python test_streaming_playback.py --text "Hello!" --voice speaker_b

# List all voices
python test_streaming_playback.py --list-voices

# Save to file instead of playing
python test_streaming_playback.py --text "Hello!" --output /tmp/test.wav
```

### Test All Voices

```bash
for voice in speaker_a speaker_b speaker_c speaker_d speaker_e speaker_f; do
  echo "Testing $voice..."
  python test_streaming_playback.py --text "Hello, I am your English tutor." --voice $voice --output "/tmp/voice_$voice.wav"
done
```

## HTTP API

The TTS server exposes a REST API when running in HTTP mode.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/voices` | List available voices |
| POST | `/synthesize` | Generate speech |

### Example: Synthesize Speech

```bash
curl -X POST http://localhost:8002/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice": "speaker_b"}' \
  | jq -r '.audio_base64' | base64 -d > hello.wav
```

### Response Format

```json
{
  "audio_base64": "...",
  "voice": "speaker_b",
  "speaker_name": "Emma",
  "text": "Hello world",
  "sample_rate": 24000,
  "format": "wav"
}
```

## Demo Audio Generation

### List Voices

`cd src/tools/demo-generator && source ../../backend/.venv/bin/activatepython regenerate_example.py --list-voices`

### Generate for a Lesson

```bash
cd src/tools/demo-generator
source ../../backend/.venv/bin/activate

# Generate all examples for lesson 15
python generate_demos.py --lesson 15

# Generate with parallel processing
python generate_demos.py --lesson 15 --parallel 3
```

### Regenerate Single Example

```bash
# Regenerate specific example
python regenerate_example.py --lesson 15 --pattern 1 --example 3

# Use different voice (Emma for more upbeat tone)
python regenerate_example.py --lesson 15 --pattern 1 --example 3 --student-voice speaker_b

# List voices from this script
python regenerate_example.py --list-voices
```

## Voice Selection Tips

| If audio sounds... | Try |
|-------------------|-----|
| Too monotone/depressed | `speaker_b` (Emma) - warmer, more upbeat |
| Too casual | `speaker_a` (Carter) - more professional |
| Garbled/distorted | Different voice entirely |

## Performance Metrics

The test script reports streaming metrics:

```
STREAMING METRICS
--------------------------------------------------
First chunk latency:    ~300ms
Total generation time:  ~1.5s (for 3s audio)
Audio duration:         3.2s
RTF (Real Time Factor): 0.47x
--------------------------------------------------
✓ REAL-TIME CAPABLE (RTF < 1.0)
```

RTF < 1.0 means audio generates faster than playback speed.

## Troubleshooting

### "Cannot connect to TTS server"

Server isn't running. Start it:
```bash
cd src/services/tts-mcp && source .venv/bin/activate && python server.py --http
```

### "No audio device"

The test script will save to file instead. Play with:
```bash
paplay /tmp/tts_streaming_output.wav
```

### Garbled audio

1. Try a different voice
2. Check for special characters in text
3. Regenerate the audio file

### Model loading slow

First load takes ~30s to load the model into GPU memory. Subsequent requests are fast.

## File Locations

| Path | Purpose |
|------|---------|
| `src/services/tts-mcp/server.py` | TTS server (HTTP + MCP) |
| `src/services/tts-mcp/test_streaming_playback.py` | Voice preview script |
| `src/services/tts-mcp/VibeVoice/demo/voices/streaming_model/` | Voice preset files (.pt) |
| `content/audio/ec1/demos/` | Generated demo audio files |
| `src/tools/demo-generator/` | Demo generation scripts |
