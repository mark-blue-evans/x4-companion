# MiniMax API shape — image understanding

**Status:** CONFIRMED 2026-05-08 against the user's Starter-plan API key.

## What works

Endpoint: `POST https://api.minimax.io/v1/coding_plan/vlm`
Auth header: `Authorization: Bearer <MINIMAX_API_KEY>`

Request body:

```json
{
  "prompt": "<full prompt — system instructions, history, current query>",
  "image_url": "data:image/png;base64,<base64-png>"
}
```

Response (truncated):

```json
{
  "content": "...",
  "base_resp": {"status_code": 0, "status_msg": "success"}
}
```

The endpoint is single-shot: no `messages` array, no system role separation. To
preserve conversation history, `MiniMaxBrain` flattens the system prompt + prior
turns + current user query into the single `prompt` string.

## What does NOT work (verified)

`POST https://api.minimax.io/v1/text/chatcompletion_v2` with a `MiniMax-M2.7`
model and an `image_url` content block in the user message **silently drops the
image**. The API returns `200 OK` with a normal text response, but the model
explicitly says "I don't see any screenshot attached." This is the wrong path
for vision and produces no error to alert you.

`scripts/minimax_smoke.py` reproduces the broken path; it's kept in the repo as
a regression check / diagnostic.

## What confirmed it

- `scripts/minimax_smoke.py` (chat endpoint, broken) → 200, model asks for the image
- `scripts/minimax_vlm_probe.py` (VLM endpoint, working) → 200, model describes the image

Both probes use `tests/fixtures/x4_screenshot.png`.
