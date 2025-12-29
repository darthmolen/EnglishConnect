# Piper TTS Service

CPU-based text-to-speech using [Piper](https://github.com/rhasspy/piper). Optimized for short utterances like vocabulary words.

## Why Piper?

- **Better for short utterances** - VibeVoice struggles with < 3 words
- **CPU-based** - No GPU required
- **Multi-language** - Native English and Spanish support
- **Fast** - Optimized ONNX inference

## Installation

### 1. Create virtual environment

```bash
cd src/services/piper
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Download voice models

```bash
cd models

# English (US) - Lessac medium quality (~63 MB)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Spanish (Mexico) - ALD medium quality (~63 MB)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx.json
```

### 3. Verify installation

```bash
# Test Piper CLI directly
echo "Hello world" | piper -m models/en_US-lessac-medium.onnx --output_file test.wav
play test.wav  # or aplay test.wav

# Test PiperService
python -c "
from service import PiperService
p = PiperService()
print('Languages:', p.get_available_languages())
audio = p.synthesize('Hello world', 'en')
print(f'Generated {len(audio)} bytes')
"
```

## Usage

### Single language synthesis

```python
from services.piper import PiperService

service = PiperService()

# English
audio_bytes = service.synthesize("Hello", language="en")

# Spanish
audio_bytes = service.synthesize("Hola", language="es")
```

### Vocabulary pronunciation (bilingual)

```python
# For vocabulary items with singular/plural forms
audio_bytes = service.synthesize_vocabulary(
    english_parts=["book", "books"],
    spanish_parts=["libro", "libros"],
    intra_pause=0.5,   # Pause between singular/plural
    inter_pause=0.8,   # Pause between languages
)

# Result: "book" [0.5s] "books" [0.8s] "libro" [0.5s] "libros"
```

## Voice Models

| Voice | Language | File | Size |
|-------|----------|------|------|
| Lessac | English (US) | en_US-lessac-medium.onnx | ~63 MB |
| ALD | Spanish (MX) | es_MX-ald-medium.onnx | ~63 MB |

### Alternative voices

Browse samples at: https://rhasspy.github.io/piper-samples/

**European Spanish:**
```bash
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx
```

**Higher quality (larger files):**
Replace `medium` with `high` in the URLs.

## Technical Details

- **Native sample rate:** 22050 Hz (Piper default)
- **Output sample rate:** 24000 Hz (resampled to match EnglishConnect audio)
- **Format:** WAV, float32
- **Pauses:** Programmatic (Piper doesn't support inline pause markers)
