# X4 Companion

AI co-pilot for X4: Foundations. Voice-in, voice-out command interface for in-game AI queries.

## Installation

**Requirements:** Windows 10/11 with Python 3.12+

```bash
git clone https://github.com/[repo]/x4-companion.git
cd x4-companion
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and fill in API keys:

```bash
MINIMAX_API_KEY=your_key_here
DEEPGRAM_API_KEY=your_key_here
```

## Usage

```bash
x4-companion
```

Hotkey: `Alt+Shift+V` to start recording, release to submit.

For detailed configuration options and design spec, see `docs/superpowers/specs/2026-05-08-x4-companion-design.md`.
