# MiniMax M2.7 + Image Understanding — API shape (TBD until smoke test)

**Status:** Untested as of 2026-05-08. Run `scripts/minimax_smoke.py` with your
`MINIMAX_API_KEY` to confirm the working request shape on the Starter plan.

## Hypothesis (used in `MiniMaxBrain` until verified)

Endpoint: `https://api.minimax.io/v1/text/chatcompletion_v2`
Auth header: `Authorization: Bearer <MINIMAX_API_KEY>`

Request body:

```json
{
  "model": "MiniMax-M2.7",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "..."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
      ]
    }
  ]
}
```

Expected response (truncated):

```json
{ "choices": [ { "message": { "content": "..." } } ] }
```

## After the smoke test

If the hypothesis above works, mark this file CONFIRMED and date it.

If it fails, replace the request body with what actually worked and update
`src/x4_companion/minimax_brain.py` to match. Likely alternates:

- A separate `image_understanding` endpoint that returns a caption, then a
  text-only chat completion with the caption inlined.
- An MCP tool invocation pattern where the client opts into a tool and the
  model calls it during the response.

Whichever is correct, document it here and update the brain implementation.
