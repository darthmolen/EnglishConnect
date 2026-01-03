# TTS + STT MCP Servers - Streamable HTTP Implementation

## Overview

Two independent MCP servers with generic tool interfaces. Backend implementations are swappable - local models now, cloud services later. The MCP interface is the contract.

| Server | Endpoint | Tools |
|--------|----------|-------|
| TTS | `http://localhost:8001/mcp` | `tts`, `voices` |
| STT | `http://localhost:8002/mcp` | `stt`, `languages` |

## Why Separate Servers

- **Different resource profiles** - STT (Whisper) is GPU/memory heavy; TTS is lighter
- **Independent scaling** - TTS likely gets 10x the traffic
- **Dependency isolation** - Whisper drags in torch/numpy; TTS might be a thin wrapper
- **Deployment flexibility** - Swap backends, different release cycles, A/B testing
- **Smaller containers** - Faster cold starts, less attack surface

## Transport Choice

**Streamable HTTP with optional SSE breakout**

- `stateless_http=True` - no session state, scales horizontally
- `json_response=False` (default) - allows SSE streaming for audio chunks
- Single endpoint per server

SSE is deprecated as a *transport architecture*, but remains available as a *response mode* within Streamable HTTP. Perfect for streaming TTS audio chunks.

## Dependencies

```
# Both servers
mcp>=1.25,<2
```

Pin to v1.x - v2 has breaking transport layer changes coming.

---

# TTS Server

## Project Structure

```
tts-mcp/
├── server.py
├── requirements.txt
├── backends/
│   ├── __init__.py
│   ├── base.py
│   ├── local.py        # VibeVoice
│   └── azure.py        # Future
```

## Server Implementation

```python
# tts-mcp/server.py
"""
TTS MCP Server
Transport: Streamable HTTP with SSE streaming for audio chunks
Endpoint: http://localhost:8001/mcp
"""

import base64
from mcp.server.fastmcp import FastMCP, Context
from backends import get_backend

mcp = FastMCP(
    "TTS",
    stateless_http=True,
)


@mcp.tool()
async def tts(text: str, voice: str = "default", ctx: Context) -> dict:
    """
    Text-to-speech synthesis. Audio chunks stream via progress notifications.
    
    Args:
        text: Text to synthesize
        voice: Voice ID
    
    Returns:
        Summary with total chunks sent
    """
    backend = get_backend(voice)
    
    chunk_count = 0
    total_bytes = 0
    
    async for audio_chunk in backend.stream(text):
        await ctx.report_progress(
            progress=chunk_count,
            total=None,
            data={
                "type": "audio_chunk",
                "index": chunk_count,
                "audio_b64": base64.b64encode(audio_chunk).decode(),
                "format": backend.format,
                "sample_rate": backend.sample_rate,
            }
        )
        chunk_count += 1
        total_bytes += len(audio_chunk)
        
    return {
        "status": "complete",
        "chunks": chunk_count,
        "bytes": total_bytes,
    }


@mcp.tool()
async def voices() -> list[dict]:
    """List available TTS voices for current backend."""
    backend = get_backend()
    return backend.list_voices()


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
    )
```

## Backend Abstraction

```python
# tts-mcp/backends/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator


class TTSBackend(ABC):
    format: str = "pcm_16bit"
    sample_rate: int = 16000
    
    @abstractmethod
    async def stream(self, text: str) -> AsyncIterator[bytes]:
        """Yield audio chunks as they generate."""
        pass
    
    @abstractmethod
    def list_voices(self) -> list[dict]:
        pass
```

```python
# tts-mcp/backends/local.py
"""Local backend - VibeVoice"""

import asyncio
from .base import TTSBackend


class VibeVoiceTTS(TTSBackend):
    format = "pcm_16bit"  # Adjust to actual output
    sample_rate = 24000    # Adjust to actual rate
    
    def __init__(self, voice: str = "default"):
        # TODO: Initialize VibeVoice synthesizer
        self.voice = voice
        
    async def stream(self, text: str):
        # TODO: Replace with actual VibeVoice streaming
        # If sync-only, use asyncio.to_thread:
        #
        # for chunk in await asyncio.to_thread(self._sync_stream, text):
        #     yield chunk
        
        for chunk in self.synth.synthesize_streaming(text):
            yield chunk
            
    def list_voices(self) -> list[dict]:
        # TODO: Return actual voice list
        return [
            {"id": "default", "name": "Default", "language": "en"},
        ]
```

```python
# tts-mcp/backends/__init__.py
import os
from .local import VibeVoiceTTS

BACKEND = os.getenv("TTS_BACKEND", "local")


def get_backend(voice: str = "default"):
    if BACKEND == "local":
        return VibeVoiceTTS(voice)
    elif BACKEND == "azure":
        from .azure import AzureTTS
        return AzureTTS(voice)
    raise ValueError(f"Unknown backend: {BACKEND}")
```

## Requirements

```
# tts-mcp/requirements.txt
mcp>=1.25,<2

# Local backend dependencies
# vibevoice  # or whatever your local TTS package is
```

---

# STT Server

## Project Structure

```
stt-mcp/
├── server.py
├── requirements.txt
├── backends/
│   ├── __init__.py
│   ├── base.py
│   ├── local.py        # Whisper
│   └── azure.py        # Future
```

## Server Implementation

```python
# stt-mcp/server.py
"""
STT MCP Server
Transport: Streamable HTTP
Endpoint: http://localhost:8002/mcp
"""

import base64
from mcp.server.fastmcp import FastMCP
from backends import get_backend

mcp = FastMCP(
    "STT",
    stateless_http=True,
)


@mcp.tool()
async def stt(audio_b64: str, language: str = "en") -> dict:
    """
    Speech-to-text transcription.
    
    Args:
        audio_b64: Base64 encoded audio
        language: Language code hint
    
    Returns:
        Transcription with optional segments
    """
    backend = get_backend()
    audio_bytes = base64.b64decode(audio_b64)
    
    result = await backend.transcribe(audio_bytes, language=language)
    
    return {
        "text": result.text,
        "language": result.language,
        "segments": result.segments,
    }


@mcp.tool()
async def languages() -> list[dict]:
    """List supported languages for current backend."""
    backend = get_backend()
    return backend.list_languages()


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8002,
    )
```

## Backend Abstraction

```python
# stt-mcp/backends/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    language: str
    segments: list[dict] | None = None


class STTBackend(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, language: str) -> TranscriptionResult:
        pass
    
    @abstractmethod
    def list_languages(self) -> list[dict]:
        pass
```

```python
# stt-mcp/backends/local.py
"""Local backend - Whisper"""

import asyncio
from .base import STTBackend, TranscriptionResult


class WhisperSTT(STTBackend):
    def __init__(self, model_size: str = "base"):
        import whisper
        self.model = whisper.load_model(model_size)
        
    async def transcribe(self, audio: bytes, language: str) -> TranscriptionResult:
        # Whisper is sync - run in thread pool
        return await asyncio.to_thread(
            self._transcribe_sync, audio, language
        )
    
    def _transcribe_sync(self, audio: bytes, language: str) -> TranscriptionResult:
        # TODO: Handle audio bytes -> temp file or numpy array
        result = self.model.transcribe(audio, language=language)
        return TranscriptionResult(
            text=result["text"],
            language=result.get("language", language),
            segments=[
                {"start": s["start"], "end": s["end"], "text": s["text"]}
                for s in result.get("segments", [])
            ]
        )
    
    def list_languages(self) -> list[dict]:
        # Whisper supports many - return common ones
        return [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "zh", "name": "Chinese"},
            {"code": "ja", "name": "Japanese"},
        ]
```

```python
# stt-mcp/backends/__init__.py
import os
from .local import WhisperSTT

BACKEND = os.getenv("STT_BACKEND", "local")


def get_backend():
    if BACKEND == "local":
        return WhisperSTT()
    elif BACKEND == "azure":
        from .azure import AzureSTT
        return AzureSTT()
    raise ValueError(f"Unknown backend: {BACKEND}")
```

## Requirements

```
# stt-mcp/requirements.txt
mcp>=1.25,<2

# Local backend dependencies
openai-whisper
torch
numpy
```

---

# Frontend Integration

## Connecting to Both Servers

```javascript
const TTS_ENDPOINT = "http://localhost:8001/mcp";
const STT_ENDPOINT = "http://localhost:8002/mcp";

async function callMCP(endpoint, tool, args) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "tools/call",
      params: { name: tool, arguments: args },
      id: Date.now()
    })
  });
  return response;
}

// TTS with streaming
async function speak(text, voice = "default") {
  const response = await callMCP(TTS_ENDPOINT, "tts", { text, voice });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    handleAudioChunk(decoder.decode(value));
  }
}

// STT - standard request/response
async function transcribe(audioBlob) {
  const base64 = await blobToBase64(audioBlob);
  const response = await callMCP(STT_ENDPOINT, "stt", { audio_b64: base64 });
  const result = await response.json();
  return result.result.text;
}
```

## Audio Chunk Player (for TTS streaming)

```javascript
class AudioChunkPlayer {
  constructor(sampleRate = 24000) {
    this.ctx = new AudioContext({ sampleRate });
    this.queue = [];
    this.playing = false;
  }
  
  enqueue(base64Chunk) {
    const bytes = Uint8Array.from(atob(base64Chunk), c => c.charCodeAt(0));
    const float32 = this.pcmToFloat32(bytes);
    this.queue.push(float32);
    if (!this.playing) this.playNext();
  }
  
  pcmToFloat32(pcmBytes) {
    const int16 = new Int16Array(pcmBytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768;
    }
    return float32;
  }
  
  playNext() {
    if (this.queue.length === 0) {
      this.playing = false;
      return;
    }
    
    this.playing = true;
    const samples = this.queue.shift();
    const buffer = this.ctx.createBuffer(1, samples.length, this.ctx.sampleRate);
    buffer.getChannelData(0).set(samples);
    
    const source = this.ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.ctx.destination);
    source.onended = () => this.playNext();
    source.start();
  }
}
```

---

# Testing

## MCP Inspector

```bash
# Terminal 1 - TTS
cd tts-mcp
mcp dev server.py

# Terminal 2 - STT
cd stt-mcp
mcp dev server.py
```

## Manual curl

```bash
# List voices
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"voices","arguments":{}},"id":1}'

# List languages
curl -X POST http://localhost:8002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"languages","arguments":{}},"id":1}'
```

---

# Deployment

## Local Development

```bash
# Terminal 1
cd tts-mcp && python server.py

# Terminal 2
cd stt-mcp && python server.py
```

## Docker (separate containers)

```dockerfile
# tts-mcp/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["python", "server.py"]
```

```dockerfile
# stt-mcp/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8002
CMD ["python", "server.py"]
```

## Kubernetes (independent scaling)

```yaml
# tts-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tts-mcp
spec:
  replicas: 3  # Scale based on traffic
  # ...

---
# stt-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stt-mcp
spec:
  replicas: 1  # GPU-bound, fewer replicas
  # ...
```

## Backend Swap (environment variable)

```bash
# Local -> Azure
export TTS_BACKEND=azure
export STT_BACKEND=azure
```

---

# Tasks for Claude Code

## TTS Server
1. [ ] Wire VibeVoice into `backends/local.py`
2. [ ] Confirm chunk format and sample rate
3. [ ] If sync-only, wrap with `asyncio.to_thread()`
4. [ ] Populate actual voice list
5. [ ] Test streaming with MCP Inspector

## STT Server
1. [ ] Wire Whisper into `backends/local.py`
2. [ ] Handle audio bytes → Whisper input (temp file or numpy)
3. [ ] Lazy-load model to avoid startup delay
4. [ ] Test with MCP Inspector

## Both
1. [ ] Add CORS if frontend is separate origin:
   ```python
   mcp = FastMCP("TTS", stateless_http=True, cors_origins=["http://localhost:3000"])
   ```
2. [ ] Frontend audio chunk handling
3. [ ] Error handling / retries
