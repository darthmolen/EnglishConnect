#!/usr/bin/env python3
"""Generate voice samples for all available TTS voices.

Creates sample audio files in content/samples/voices/ so users can
listen and choose the best voice for vocabulary pronunciation.

Usage:
    python src/tools/generate_voice_samples.py
"""

import asyncio
import base64
from pathlib import Path

import httpx

# TTS service configuration
TTS_URL = "http://localhost:8002"

# Sample text for pronunciation demonstration
SAMPLE_TEXT = "Hello, my name is {name}. Book. Books."

# Output directory
OUTPUT_DIR = Path("content/samples/voices")

# Voice configurations (matching server.py)
VOICES = {
    "speaker_a": {"name": "Carter", "description": "Male English speaker (clear, professional)"},
    "speaker_b": {"name": "Emma", "description": "Female English speaker (warm, friendly)"},
    "speaker_c": {"name": "Davis", "description": "Male English speaker (conversational)"},
    "speaker_d": {"name": "Grace", "description": "Female English speaker (clear, articulate)"},
    "speaker_e": {"name": "Frank", "description": "Male English speaker (authoritative)"},
    "speaker_f": {"name": "Mike", "description": "Male English speaker (casual, friendly)"},
}


async def generate_sample(voice_id: str, voice_info: dict) -> bool:
    """Generate a sample audio file for a voice."""
    text = SAMPLE_TEXT.format(name=voice_info["name"])
    output_file = OUTPUT_DIR / f"{voice_id}_{voice_info['name'].lower()}.wav"

    print(f"Generating sample for {voice_id} ({voice_info['name']})...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{TTS_URL}/synthesize",
                json={"text": text, "voice": voice_id},
                timeout=60.0,
            )
            response.raise_for_status()

            result = response.json()
            audio_data = base64.b64decode(result["audio_base64"])

            output_file.write_bytes(audio_data)
            print(f"  ✓ Saved: {output_file}")
            return True

        except httpx.HTTPError as e:
            print(f"  ✗ Error: {e}")
            return False


async def main():
    """Generate samples for all voices sequentially (to avoid TTS overload)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating voice samples in {OUTPUT_DIR}/")
    print("=" * 50)

    success_count = 0
    for voice_id, voice_info in VOICES.items():
        if await generate_sample(voice_id, voice_info):
            success_count += 1

    print("=" * 50)
    print(f"Generated {success_count}/{len(VOICES)} samples")

    if success_count > 0:
        print(f"\nListen to samples in: {OUTPUT_DIR}/")
        print("Voice descriptions:")
        for voice_id, info in VOICES.items():
            print(f"  {voice_id}: {info['description']}")


if __name__ == "__main__":
    asyncio.run(main())
