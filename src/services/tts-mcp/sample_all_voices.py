#!/usr/bin/env python3
"""Sample all available TTS voices."""

import subprocess
import sys

VOICES = ["speaker_a", "speaker_b", "speaker_c", "speaker_d", "speaker_e", "speaker_f"]
TEXT = "Hello, I am your English tutor."


def main():
    for voice in VOICES:
        print(f"Testing {voice}...")
        output_path = f"/tmp/voice_{voice}.wav"
        result = subprocess.run(
            [
                sys.executable,
                "test_streaming_playback.py",
                "--text", TEXT,
                "--voice", voice,
                "--output", output_path,
            ],
            check=False,
        )
        if result.returncode != 0:
            print(f"  Failed with exit code {result.returncode}")
        else:
            print(f"  Saved to {output_path}")


if __name__ == "__main__":
    main()
