"""End-to-end check of MiniMaxBrain against the live VLM endpoint."""
from __future__ import annotations
import asyncio
import os
import sys
from pathlib import Path

from x4_companion.minimax_brain import MiniMaxBrain

api_key = os.environ.get("MINIMAX_API_KEY")
if not api_key:
    print("set MINIMAX_API_KEY", file=sys.stderr)
    sys.exit(2)

img_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "x4_screenshot.png"
frame = img_path.read_bytes()


async def main() -> None:
    brain = MiniMaxBrain(api_key=api_key, vkb_bindings="A4 HAT Press -- Deselects target")
    try:
        reply1 = await brain.answer(frame, "Describe what you see in one sentence.")
        print(f"Q1 reply: {reply1}")
        reply2 = await brain.answer(frame, "What color did you say it was?")
        print(f"Q2 reply (history check): {reply2}")
    finally:
        await brain.aclose()


asyncio.run(main())
