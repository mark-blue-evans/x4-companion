# Manual test plan — X4 Companion

Run on the **Windows gaming PC**. The WSL dev machine can't reach the GPU/mic/keyboard the same way.

## Prereqs
- Repo cloned, `pip install -e ".[dev]"` complete (or use `uv` as on the dev machine)
- `MINIMAX_API_KEY` + `DEEPGRAM_API_KEY` in env
- X4 Foundations installed; set graphics mode to **Borderless Windowed** (not Exclusive Fullscreen)
- VKB controller bound to send the `Home` key for PTT (or use the keyboard `Home` key)

## Run

    python -m x4_companion

## Smoke checks (no game running yet)

1. Tray icon appears.
2. Press `Home`, hold for 1s, say "hello", release.
3. Within ~3s: overlay shows a reply, TTS speaks it.
4. Right-click tray → Quit. Process exits cleanly.

## In-game checks (X4 launched, borderless)

1. Press `Home`, ask "what is on my screen?". Reply describes the X4 UI.
2. Hold `Home`, say nothing, release within 200ms → overlay says "(didn't catch that)".
3. Pull network → press `Home`, ask anything → overlay shows "(brain error: ...)".
4. Switch X4 to Exclusive Fullscreen → overlay says "(capture failed: ...)" instead of crashing.
5. Ask 3 follow-up questions in a row; answers should reflect awareness of prior turns.

## Latency

- Stopwatch from PTT release to first audible word. Target ≤3s.

## Quota check

- After ~30 questions in a session, no rate limit errors. (1500 reqs / 5h = ~750 PTT turns.)
