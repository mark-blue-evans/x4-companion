# X4 Companion

A voice companion for X4: Foundations. Push-to-talk, asks MiniMax M2.7 (with image
understanding), replies via Deepgram Aura-2 voice + a transparent overlay.
Built around the [codejnki/x4_vkb](https://github.com/codejnki/x4_vkb) VKB
Gladiator NTX EVO dual-stick keybinding profile — the assistant knows your
button layout and answers in terms of what to press on your sticks.

## How it runs

There is no installer or `.exe`. You run it from source:

```
python -m x4_companion
```

That's the whole thing. To update later: `git pull && python -m x4_companion`.

## Install (Windows gaming PC)

Requires Python 3.12+.

```
git clone https://github.com/<owner>/x4-companion.git
cd x4-companion
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

(`pip install -e ".[dev]"` if you also want the test suite.)

## API keys (do **not** commit these)

The repo is public — never put API keys in any file that's committed.
`.env` is gitignored; the only file that holds keys is `.env` on your gaming
PC, created from `.env.example`:

```
copy .env.example .env
```

Then edit `.env`:

```
MINIMAX_API_KEY=mxp-...
DEEPGRAM_API_KEY=...
```

System environment variables also work and take precedence over `.env`.

## Run

X4 must be in **Borderless Windowed** (capture won't work in Exclusive Fullscreen).

```
.venv\Scripts\activate
python -m x4_companion
```

A tray icon appears. Press and hold **Home** (or whichever key you bind your
VKB controller to send), speak your question, release. The reply shows in a
small overlay top-right and is spoken aloud.

## Configuration

Optional `~/.x4-companion/config.toml`:

```toml
[hotkey]
key = "home"

[voice]
model = "aura-2-thalia-en"

[brain]
model = "MiniMax-M2.7"
history_turns = 6

[overlay]
position = "top-right"
opacity = 0.85
font_size = 16
fade_seconds = 30
```

Full config reference: `docs/superpowers/specs/2026-05-08-x4-companion-design.md`.

## VKB context

The repo bundles a copy of the codejnki/x4_vkb README at
`src/x4_companion/data/vkb_bindings.md`. It's loaded at startup and prepended
to the assistant's system prompt, so when you ask "how do I dock?" it'll point
you at a specific VKB stick button rather than a generic keyboard shortcut.

If you remap your sticks, edit that file (or replace it) and restart.

## Manual test plan

After install, walk through `docs/manual-test.md` once to verify capture,
mic, hotkey, overlay, and quota all behave.
