# Frontend Timing Instrumentation

Add these timing points to your frontend for complete latency visibility.

## TTS Pipeline (T0, T10, T11)

Add to your conversation handling code:

```typescript
// In your conversation/practice component

async function sendMessage(message: string) {
  const requestId = crypto.randomUUID().slice(0, 8);

  // T0: Request sent
  const t0 = performance.now();
  console.log(`[TIMING] request_id=${requestId} point=T0 ts=${Date.now()/1000} label="request_sent"`);

  try {
    const response = await fetch('/api/practice/conversation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': requestId,  // Correlate with backend
      },
      body: JSON.stringify({
        message,
        lesson_number: lessonNumber,
        mode: mode,
        // ... other fields
      }),
    });

    // T10: First byte received (approximate)
    const t10 = performance.now();
    console.log(`[TIMING] request_id=${requestId} point=T10 ts=${Date.now()/1000} label="response_received" delta_ms=${(t10-t0).toFixed(1)}`);

    const data = await response.json();

    // Play audio if present
    if (data.audio_base64) {
      playAudio(data.audio_base64, requestId, t0);
    }

  } catch (error) {
    console.error('Request failed:', error);
  }
}

function playAudio(audioBase64: string, requestId: string, t0: number) {
  const audioBlob = base64ToBlob(audioBase64, 'audio/wav');
  const audioUrl = URL.createObjectURL(audioBlob);
  const audio = new Audio(audioUrl);

  audio.onplay = () => {
    // T11: Audio playback starts
    const t11 = performance.now();
    console.log(`[TIMING] request_id=${requestId} point=T11 ts=${Date.now()/1000} label="audio_playback_start" total_ms=${(t11-t0).toFixed(1)}`);
  };

  audio.play();
}

function base64ToBlob(base64: string, mimeType: string): Blob {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return new Blob([bytes], { type: mimeType });
}
```

## STT Pipeline (S0, S1, S5)

Add to your recording component:

```typescript
// In your audio recording component

let recordingStartTime: number;
let currentRequestId: string;

function startRecording() {
  currentRequestId = crypto.randomUUID().slice(0, 8);
  recordingStartTime = performance.now();

  // S0: Recording starts
  console.log(`[TIMING] request_id=${currentRequestId} point=S0 ts=${Date.now()/1000} label="recording_start"`);

  // Start MediaRecorder...
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      // ... setup recording
    });
}

async function stopRecordingAndTranscribe(audioBlob: Blob) {
  // S1: Recording ends, audio sent
  const s1 = performance.now();
  console.log(`[TIMING] request_id=${currentRequestId} point=S1 ts=${Date.now()/1000} label="recording_end" duration_ms=${(s1-recordingStartTime).toFixed(1)}`);

  // Send to STT service
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');

  try {
    const response = await fetch('http://localhost:8001/transcribe', {
      method: 'POST',
      headers: {
        'X-Request-ID': currentRequestId,
      },
      body: formData,
    });

    // S5: Result received
    const s5 = performance.now();
    const data = await response.json();
    console.log(`[TIMING] request_id=${currentRequestId} point=S5 ts=${Date.now()/1000} label="stt_result_received" delta_ms=${(s5-s1).toFixed(1)} text="${data.text?.slice(0, 50)}..."`);

    return data.text;

  } catch (error) {
    console.error('Transcription failed:', error);
    throw error;
  }
}
```

## Analyzing Timing Logs

Collect logs from:
1. **Browser console** - T0, T10, T11, S0, S1, S5
2. **Backend logs** - T1, T2, T3, T4, T5, T9
3. **TTS server logs** - T6, T7, T8
4. **STT server logs** - S2, S3, S4

### Calculate Key Metrics

```
TTS Pipeline:
- Total perceived latency: T11 - T0
- Backend processing: T9 - T1
- LLM latency: T3 - T2 (per iteration)
- TTS synthesis: T8 - T6
- TTS network overhead: (T5 - T4) - (T8 - T6)
- Frontend audio prep: T11 - T10

STT Pipeline:
- Recording duration: S1 - S0
- Total transcription: S5 - S1
- Server processing: S4 - S2
- Model inference: S4 - S3
- Network overhead: (S5 - S1) - (S4 - S2)
```

### Sample Log Output

```
# Frontend
[TIMING] request_id=abc123 point=T0 ts=1704000000.000 label="request_sent"
[TIMING] request_id=abc123 point=T10 ts=1704000001.234 label="response_received" delta_ms=1234.0
[TIMING] request_id=abc123 point=T11 ts=1704000001.250 label="audio_playback_start" total_ms=1250.0

# Backend
[TIMING] request_id=abc123 point=T1 ts=1704000000.050 label="request_received"
[TIMING] request_id=abc123 point=T2 ts=1704000000.060 label="llm_start" iteration=1
[TIMING] request_id=abc123 point=T3 ts=1704000000.400 label="llm_complete" iteration=1 tokens=150 delta_ms=340.0
[TIMING] request_id=abc123 point=T4 ts=1704000000.410 label="tool_start" tool=speak
[TIMING] request_id=abc123 point=T5 ts=1704000000.850 label="tool_complete" tool=speak delta_ms=440.0
[TIMING] request_id=abc123 point=T9 ts=1704000000.860 label="response_sent"

# TTS Server
[TIMING] request_id=abc123 point=T6 ts=1704000000.420 label="synthesis_start"
[TIMING] request_id=abc123 point=T7 ts=1704000000.450 label="inference_start"
[TIMING] request_id=abc123 point=T8 ts=1704000000.840 label="synthesis_complete" delta_ms=420.0
```
