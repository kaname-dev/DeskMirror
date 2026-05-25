#!/usr/bin/env python3
"""Generate short stereo banner sound (BCWAV: <=3s, 2 channels)."""

import struct
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "resources" / "audio.wav"
RATE = 44100
CHANNELS = 2
DURATION_SEC = 1.5


def main() -> None:
    nframes = int(RATE * DURATION_SEC)
    # Soft fade-in/out sine blip (very quiet)
    samples = []
    for i in range(nframes):
        t = i / RATE
        env = 1.0
        if t < 0.05:
            env = t / 0.05
        elif t > DURATION_SEC - 0.05:
            env = max(0.0, (DURATION_SEC - t) / 0.05)
        v = int(1200 * env * (0.4 + 0.6 * (i % 200) / 200))
        for _ in range(CHANNELS):
            samples.append(struct.pack("<h", v))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(b"".join(samples))
    print(f"Wrote {OUT} ({DURATION_SEC}s, {CHANNELS}ch)")


if __name__ == "__main__":
    main()
