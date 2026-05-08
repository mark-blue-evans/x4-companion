"""Probe whether /v1/coding_plan/vlm supports streaming via stream:true.

We test:
1. Adding "stream": true to the JSON body
2. Reading the response with iter_lines / iter_bytes
3. Looking for SSE-style "data: ..." chunks vs a single buffered JSON
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

body = {
    "prompt": "Describe this screenshot in 3 sentences.",
    "image_url": f"data:image/png;base64,{img_b64}",
    "stream": True,
}

url = "https://api.minimax.io/v1/coding_plan/vlm"
headers = {"Authorization": f"Bearer {api_key}"}

print("--- Test 1: streaming with stream=true ---")
with httpx.stream("POST", url, headers=headers, json=body, timeout=60.0) as r:
    print(f"status: {r.status_code}")
    print(f"content-type: {r.headers.get('content-type')}")
    chunk_count = 0
    total_bytes = 0
    for chunk in r.iter_text():
        chunk_count += 1
        total_bytes += len(chunk)
        if chunk_count <= 5:
            print(f"  chunk[{chunk_count}] ({len(chunk)} chars): {chunk[:200]!r}")
    print(f"total: {chunk_count} chunks, {total_bytes} chars")

print("\n--- Test 2: same body without stream key (baseline) ---")
body_baseline = {k: v for k, v in body.items() if k != "stream"}
with httpx.stream("POST", url, headers=headers, json=body_baseline, timeout=60.0) as r:
    print(f"status: {r.status_code}")
    print(f"content-type: {r.headers.get('content-type')}")
    chunk_count = 0
    for chunk in r.iter_text():
        chunk_count += 1
        if chunk_count == 1:
            print(f"  chunk[1] ({len(chunk)} chars): {chunk[:300]!r}")
    print(f"total: {chunk_count} chunks")
