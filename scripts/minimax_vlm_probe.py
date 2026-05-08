"""Probe MiniMax VLM endpoint /v1/coding_plan/vlm with a screenshot."""
from __future__ import annotations
import base64
import os
import sys
from pathlib import Path

import httpx

api_key = os.environ.get("MINIMAX_API_KEY")
if not api_key:
    print("set MINIMAX_API_KEY", file=sys.stderr)
    sys.exit(2)

img_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "x4_screenshot.png"
img_b64 = base64.b64encode(img_path.read_bytes()).decode()

r = httpx.post(
    "https://api.minimax.io/v1/coding_plan/vlm",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "prompt": "Describe this screenshot in one sentence.",
        "image_url": f"data:image/png;base64,{img_b64}",
    },
    timeout=60.0,
)
print("status:", r.status_code)
print(r.text[:2000])
