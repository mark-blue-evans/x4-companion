"""
Probe MiniMax M2.7 with an image + question.

Usage:
    MINIMAX_API_KEY=... python scripts/minimax_smoke.py

Expected outcomes:
- 200 with a sensible reply describing the screenshot:
  the image_url content-block pattern works on M2.7 directly. Update
  docs/minimax-api-shape.md to confirm, and proceed.
- 4xx with "image not supported on this model":
  M2.7 doesn't take inline images. Image understanding goes through a
  separate path (likely an MCP tool or a dedicated VLM endpoint). Read
  https://platform.minimax.io/docs and adapt this script.
- 401/403:
  API key wrong, or this plan tier doesn't include image understanding.
"""
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

payload = {
    "model": "MiniMax-M2.7",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this screenshot in one sentence."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            ],
        }
    ],
}

r = httpx.post(
    "https://api.minimax.io/v1/text/chatcompletion_v2",
    headers={"Authorization": f"Bearer {api_key}"},
    json=payload,
    timeout=60.0,
)
print("status:", r.status_code)
print(r.text[:2000])
