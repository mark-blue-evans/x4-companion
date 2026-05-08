# X4 Foundations Companion — Design

**Date:** 2026-05-08
**Status:** Draft for review

## Goal

A Windows desktop companion that watches the X4 Foundations screen and answers
questions on demand by voice. Acts like an experienced X4 player sitting next to
the user — can be asked anything ("what's this ship?", "should I buy this?",
"where do I find energy cells?") and replies verbally with a transcript overlay.

## Non-goals (v1)

- No autonomous suggestions / interruptions while playing
- No always-on speech recognition (push-to-talk only)
- No game-state extraction via memory reading or save-file parsing
- No multiplayer / multi-user
- No mobile or web client
- No long-term memory / persona across sessions

## User flow

1. User launches the companion on the Windows gaming PC. Tray icon appears.
2. User starts X4 and plays normally.
3. When user has a question:
   - Holds the configured PTT key (default: `Home`; user binds a VKB controller
     button to send `Home`).
   - Speaks: "What faction owns this station?"
   - Releases the key.
4. Companion captures the current screen frame, transcribes the audio, sends
   both to MiniMax M2.7 (which calls the image-understanding MCP tool internally
   to perceive the frame), and receives a text reply.
5. Reply is spoken via Deepgram Aura-2 TTS and displayed in a subtle
   always-on-top overlay (corner of screen, semi-transparent).
6. Conversation context (last N turns) persists in-process so user can ask
   follow-ups in the same session.

Round-trip target: ≤3s from PTT release to first audio.

## Architecture

Single-process Python application on Windows. No build step in v1 — runs as
`python companion.py`. Three concurrent loops via asyncio:

```
[Capture loop]    keeps a current-frame buffer; sampled on demand
[Hotkey loop]     listens for PTT down/up via global keyboard hook
[Conversation]    on PTT up: STT → Brain.answer(frame, query) → TTS → overlay
```

External dependencies:

- **MiniMax M2.7** — text reasoning, with image-understanding MCP tool
- **Deepgram** — Nova-3 STT, Aura-2 TTS (account already exists)
- **dxcam** — DXGI Desktop Duplication capture
- **PySide6** — overlay window + tray icon
- **sounddevice** — mic input + speaker output
- **keyboard** — global hotkey

```
┌────────────────────────────────────────────────────┐
│            X4 Foundations (Windows)                │
└────────────────────────────────────────────────────┘
                       │ DXGI Desktop Duplication
                       ▼
┌────────────────────────────────────────────────────┐
│  X4 Companion (Python)                             │
│                                                    │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐       │
│  │ Capturer │  │  Hotkey  │  │   Overlay   │       │
│  │ (dxcam)  │  │  (Home)  │  │  (PySide6)  │       │
│  └──────────┘  └──────────┘  └─────────────┘       │
│        │           │               ▲               │
│        ▼           ▼               │               │
│  ┌────────────────────────────────────────┐        │
│  │            Conversation Loop           │        │
│  │   1. on PTT down: start mic record     │        │
│  │   2. on PTT up: grab frame + audio     │        │
│  │   3. STT (Deepgram)  → transcript      │        │
│  │   4. Brain.answer(frame, transcript)   │        │
│  │   5. TTS (Aura-2)    → speakers        │        │
│  │   6. push reply text → overlay         │        │
│  └────────────────────────────────────────┘        │
│                  │                                 │
│                  ▼                                 │
│  ┌────────────────────────────────────────┐        │
│  │  Brain  (swappable interface)          │        │
│  │  default: MiniMaxBrain (M2.7 + image   │        │
│  │  understanding MCP); history in-process│        │
│  └────────────────────────────────────────┘        │
└────────────────────────────────────────────────────┘
```

## Components

| Module        | Purpose                                                        |
|---------------|----------------------------------------------------------------|
| `capture.py`  | dxcam-backed screen capture; `get_current_frame() -> bytes`    |
| `hotkey.py`   | Global PTT hotkey listener; emits `on_ptt_down`, `on_ptt_up`   |
| `audio.py`    | Mic recording (start/stop) + speaker playback                  |
| `stt.py`      | Deepgram Nova-3 wrapper                                        |
| `tts.py`      | Deepgram Aura-2 wrapper                                        |
| `brain.py`    | `Brain` interface + `MiniMaxBrain`; conversation history       |
| `overlay.py`  | PySide6 always-on-top transparent window                       |
| `tray.py`     | System tray icon + menu (settings, quit)                       |
| `config.py`   | TOML config loader (hotkey, devices, voice, API keys)          |
| `app.py`      | Entry point; wires loops together                              |

Each module has a single responsibility and communicates via small typed
interfaces. None of them know about each other beyond the interfaces they
consume — so swapping (e.g., a different STT provider) is local to one module.

## Data flow (one PTT turn)

```
user holds Home  → hotkey.py emits on_ptt_down
  → audio.py starts recording mic
user releases    → hotkey.py emits on_ptt_up
  → audio.py stops, returns wav bytes
  → capture.py.get_current_frame() returns PNG bytes
  → stt.py transcribes wav → "what faction owns this station"
  → brain.py.answer(frame, query):
        - appends user turn to history
        - calls MiniMax M2.7 chat API
        - frame attached for image-understanding MCP tool
        - returns assistant reply text
  → tts.py streams reply audio to speakers
  → overlay.py displays reply text (fades after 30s or next turn)
```

## Configuration

`~/.x4-companion/config.toml`:

```toml
[hotkey]
key = "home"   # bind VKB controller to send this key

[audio]
input_device = ""    # empty = system default
output_device = ""

[voice]
provider = "deepgram"
model = "aura-2-thalia-en"

[brain]
provider = "minimax"
model = "MiniMax-M2.7"
image_understanding = true
history_turns = 6

[overlay]
position = "top-right"
opacity = 0.85
font_size = 16
fade_seconds = 30
```

API keys are read from environment variables (`MINIMAX_API_KEY`,
`DEEPGRAM_API_KEY`), not the config file.

## Error handling

| Case                                  | Behavior                                                                    |
|---------------------------------------|-----------------------------------------------------------------------------|
| Network error mid-call                | Overlay: "(connection lost — try again)". History not appended.             |
| MiniMax 429 / rate limit              | Overlay: "(rate limit — wait a moment)".                                    |
| Mic returns < 200ms of audio          | Overlay: "(didn't catch that)". No API calls made.                          |
| Capture fails (fullscreen exclusive)  | Try DXGI; fall back to GDI; if both fail: "(set X4 to borderless windowed)" |
| MCP image tool refuses                | Treat as no visual context; M2.7 answers from text alone with caveat.       |
| TTS fails                             | Show overlay text only; log warning.                                        |
| Tray exit                             | Cleanly stop loops; flush state.                                            |

## Testing

- **Unit:** `brain.py` with stubbed MiniMax client; `stt.py` / `tts.py` with
  recorded fixtures; `capture.py` with a known PNG.
- **Integration:** end-to-end smoke test with real APIs but a static screenshot
  and a pre-recorded audio clip.
- **Manual:** the only way to verify the full UX (overlay z-order over
  fullscreen X4, audio ducking, hotkey while game has focus). Documented as a
  manual test plan in `docs/manual-test.md`.

## Dev workflow

- Code lives in this repo (developed in WSL on the dev machine).
- Sync to gaming PC via Git (push/pull) or SMB share.
- On the gaming PC: install Python 3.12+, `pip install -r requirements.txt`,
  set the two env vars, run `python -m x4_companion`.
- No PyInstaller, no build, no installer in v1.

## Open questions

- Default voice — `aura-2-thalia-en` proposed; user may prefer another.
- Should the companion auto-start when X4 launches? Deferred — manual launch
  is fine for v1.
- Conversation history depth — `history_turns = 6` is a guess; tune after
  first play session.
- Knowledge base injection (X4 wiki dump as RAG context) — not v1, but worth
  flagging as an obvious next step.

## Future (not v1)

- Optional autonomous mode with chime threshold
- Game-state via X4's signal callbacks (mod-side hook) for richer context
- X4 wiki RAG for grounded factual answers
- Voice cloning (MiniMax-Speech) for a custom persona
- Multi-game brain (rename to "Game Companion")
