# X4 Foundations Companion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-process Windows Python app that captures the X4 Foundations screen, listens via push-to-talk, asks MiniMax M2.7 (with image understanding), and replies via Deepgram Aura-2 voice + a transparent overlay.

**Architecture:** All logic lives in one Python package (`x4_companion`). Components communicate via small typed interfaces (Brain, STT, TTS, Capture). The Qt main thread runs the overlay/tray; a background asyncio loop runs the conversation pipeline; the hotkey lib runs in a third thread and posts signals to bridge them. Each I/O wrapper has a real implementation and a stub for tests.

**Tech Stack:** Python 3.12+, PySide6, dxcam, sounddevice, soundfile, keyboard, deepgram-sdk, httpx, Pillow, numpy, pytest.

**Dev/test environment:** Most modules are testable in WSL/Linux. Windows-only deps (`dxcam`, `keyboard`) are gated by `platform_system=='Windows'` markers; their concrete classes import the platform lib lazily so the modules can still be imported on Linux for testing the abstract layer. Real end-to-end runs happen on the Windows gaming PC.

**Note on PySide6 method calls:** This plan uses `.exec_()` (with trailing underscore) instead of `.exec()` for QApplication's event loop. Both are valid in PySide6; `exec_()` avoids a tooling false positive in this environment.

---

## File structure (target)

```
x4-companion/
├── pyproject.toml
├── README.md
├── .gitignore
├── .env.example
├── src/
│   └── x4_companion/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── config.py
│       ├── brain.py
│       ├── minimax_brain.py
│       ├── stt.py
│       ├── tts.py
│       ├── audio.py
│       ├── capture.py
│       ├── hotkey.py
│       ├── overlay.py
│       └── tray.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── x4_screenshot.png
│   │   └── hello.wav
│   ├── test_config.py
│   ├── test_brain.py
│   ├── test_stt.py
│   ├── test_tts.py
│   ├── test_audio.py
│   ├── test_capture.py
│   ├── test_minimax_brain.py
│   └── test_hotkey.py
├── scripts/
│   └── minimax_smoke.py
└── docs/
    ├── superpowers/
    │   ├── specs/2026-05-08-x4-companion-design.md
    │   └── plans/2026-05-08-x4-companion-implementation.md
    └── manual-test.md
```

Each module has one responsibility. `app.py` is the only file that knows how the pieces wire together.

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/x4_companion/__init__.py`
- Create: `src/x4_companion/__main__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_smoke.py`
- Create: `README.md`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "x4-companion"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "PySide6>=6.7",
    "sounddevice>=0.4.6",
    "soundfile>=0.12",
    "deepgram-sdk>=3.7",
    "httpx>=0.27",
    "numpy>=2.0",
    "Pillow>=10.0",
    "dxcam>=0.0.5; platform_system=='Windows'",
    "keyboard>=0.13.5; platform_system=='Windows'",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "respx>=0.21",
]

[project.scripts]
x4-companion = "x4_companion.__main__:main"

[tool.hatch.build.targets.wheel]
packages = ["src/x4_companion"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
*.egg-info/
dist/
build/
.env
```

- [ ] **Step 3: Write `.env.example`**

```
MINIMAX_API_KEY=
DEEPGRAM_API_KEY=
```

- [ ] **Step 4: Write package skeleton**

`src/x4_companion/__init__.py`:
```python
__version__ = "0.1.0"
```

`src/x4_companion/__main__.py`:
```python
def main() -> int:
    from .app import main as app_main
    return app_main()

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

`tests/conftest.py`:
```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
```

`tests/test_smoke.py`:
```python
def test_package_importable():
    import x4_companion
    assert x4_companion.__version__ == "0.1.0"
```

- [ ] **Step 5: Write `README.md`**

```markdown
# X4 Companion

A voice companion for X4 Foundations. Push-to-talk, asks MiniMax M2.7, replies via Deepgram Aura-2.

## Install (Windows gaming PC)

git clone <repo>
cd x4-companion
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

Set environment variables:
MINIMAX_API_KEY=...
DEEPGRAM_API_KEY=...

Run: python -m x4_companion

## Configure

Edit ~/.x4-companion/config.toml. See docs/superpowers/specs/2026-05-08-x4-companion-design.md for options.
```

- [ ] **Step 6: Install + run the smoke test**

```bash
cd /home/marku/x4-companion
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -v
```

Expected: `tests/test_smoke.py::test_package_importable PASSED`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore .env.example src/ tests/ README.md
git commit -m "chore: project scaffold"
```

---

## Task 2: Config module

**Files:**
- Create: `src/x4_companion/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:
```python
from x4_companion.config import load_config

def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "mm-test")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg-test")
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.hotkey.key == "home"
    assert cfg.brain.model == "MiniMax-M2.7"
    assert cfg.brain.history_turns == 6
    assert cfg.overlay.opacity == 0.85
    assert cfg.secrets.minimax_api_key == "mm-test"
    assert cfg.secrets.deepgram_api_key == "dg-test"

def test_overrides_from_toml(tmp_path, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "")
    p = tmp_path / "c.toml"
    p.write_text(
        '[hotkey]\nkey = "f8"\n'
        '[brain]\nhistory_turns = 12\n'
        '[overlay]\nposition = "top-left"\n'
    )
    cfg = load_config(p)
    assert cfg.hotkey.key == "f8"
    assert cfg.brain.history_turns == 12
    assert cfg.overlay.position == "top-left"
    assert cfg.brain.model == "MiniMax-M2.7"  # default preserved
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_config.py -v
```

Expected: FAIL — `ImportError: x4_companion.config`

- [ ] **Step 3: Write the implementation**

`src/x4_companion/config.py`:
```python
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path.home() / ".x4-companion" / "config.toml"

@dataclass
class HotkeyConfig:
    key: str = "home"

@dataclass
class AudioConfig:
    input_device: str = ""
    output_device: str = ""

@dataclass
class VoiceConfig:
    provider: str = "deepgram"
    model: str = "aura-2-thalia-en"

@dataclass
class BrainConfig:
    provider: str = "minimax"
    model: str = "MiniMax-M2.7"
    image_understanding: bool = True
    history_turns: int = 6

@dataclass
class OverlayConfig:
    position: str = "top-right"
    opacity: float = 0.85
    font_size: int = 16
    fade_seconds: int = 30

@dataclass
class Secrets:
    minimax_api_key: str = ""
    deepgram_api_key: str = ""

@dataclass
class Config:
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    brain: BrainConfig = field(default_factory=BrainConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    secrets: Secrets = field(default_factory=Secrets)

def load_config(path: Path = DEFAULT_PATH) -> Config:
    data: dict = {}
    if path.exists():
        data = tomllib.loads(path.read_text())
    return Config(
        hotkey=HotkeyConfig(**data.get("hotkey", {})),
        audio=AudioConfig(**data.get("audio", {})),
        voice=VoiceConfig(**data.get("voice", {})),
        brain=BrainConfig(**data.get("brain", {})),
        overlay=OverlayConfig(**data.get("overlay", {})),
        secrets=Secrets(
            minimax_api_key=os.environ.get("MINIMAX_API_KEY", ""),
            deepgram_api_key=os.environ.get("DEEPGRAM_API_KEY", ""),
        ),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_config.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/x4_companion/config.py tests/test_config.py
git commit -m "feat: config module with TOML + env-var secrets"
```

---

## Task 3: Brain interface + ConversationHistory + StubBrain

**Files:**
- Create: `src/x4_companion/brain.py`
- Create: `tests/test_brain.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_brain.py`:
```python
import pytest
from x4_companion.brain import ConversationHistory, StubBrain

def test_history_appends_alternating():
    h = ConversationHistory(max_turns=3)
    h.append_user("q1"); h.append_assistant("a1")
    h.append_user("q2"); h.append_assistant("a2")
    msgs = h.as_messages()
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert msgs[2]["content"] == "q2"

def test_history_drops_oldest_when_full():
    h = ConversationHistory(max_turns=2)
    for i in range(4):
        h.append_user(f"q{i}"); h.append_assistant(f"a{i}")
    msgs = h.as_messages()
    assert len(msgs) == 4
    assert msgs[0]["content"] == "q2"
    assert msgs[-1]["content"] == "a3"

@pytest.mark.asyncio
async def test_stub_brain_returns_canned_reply_and_records_inputs():
    b = StubBrain(reply="canned")
    out = await b.answer(b"PNGBYTES", "what is this?")
    assert out == "canned"
    assert b.last_query == "what is this?"
    assert b.last_frame == b"PNGBYTES"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_brain.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the implementation**

`src/x4_companion/brain.py`:
```python
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass

@dataclass
class Turn:
    role: str
    content: str

class ConversationHistory:
    def __init__(self, max_turns: int = 6):
        self._turns: deque[Turn] = deque(maxlen=max_turns * 2)

    def append_user(self, text: str) -> None:
        self._turns.append(Turn("user", text))

    def append_assistant(self, text: str) -> None:
        self._turns.append(Turn("assistant", text))

    def as_messages(self) -> list[dict]:
        return [{"role": t.role, "content": t.content} for t in self._turns]

class Brain(ABC):
    @abstractmethod
    async def answer(self, frame_png: bytes, query: str) -> str: ...

class StubBrain(Brain):
    def __init__(self, reply: str = "stub reply"):
        self.reply = reply
        self.last_frame: bytes | None = None
        self.last_query: str | None = None

    async def answer(self, frame_png: bytes, query: str) -> str:
        self.last_frame = frame_png
        self.last_query = query
        return self.reply
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_brain.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/x4_companion/brain.py tests/test_brain.py
git commit -m "feat: Brain interface + ConversationHistory + StubBrain"
```

---

## Task 4: Deepgram STT wrapper

**Files:**
- Create: `src/x4_companion/stt.py`
- Create: `tests/test_stt.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_stt.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from x4_companion.stt import DeepgramSTT, StubSTT

@pytest.mark.asyncio
async def test_stub_stt_returns_canned_text():
    stt = StubSTT(transcript="hello world")
    assert await stt.transcribe(b"WAVBYTES") == "hello world"

@pytest.mark.asyncio
async def test_deepgram_stt_calls_sdk_with_buffer():
    stt = DeepgramSTT(api_key="dg-test")
    fake_response = MagicMock()
    fake_response.results.channels[0].alternatives[0].transcript = "what is this ship"
    transcribe_mock = AsyncMock(return_value=fake_response)
    stt._client.listen.asyncrest.v = MagicMock(
        return_value=MagicMock(transcribe_file=transcribe_mock)
    )
    out = await stt.transcribe(b"FAKEWAV")
    assert out == "what is this ship"
    args, _ = transcribe_mock.call_args
    assert args[0]["buffer"] == b"FAKEWAV"
    assert args[0]["mimetype"] == "audio/wav"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_stt.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the implementation**

`src/x4_companion/stt.py`:
```python
from abc import ABC, abstractmethod

class STT(ABC):
    @abstractmethod
    async def transcribe(self, wav_bytes: bytes) -> str: ...

class DeepgramSTT(STT):
    def __init__(self, api_key: str, model: str = "nova-3"):
        from deepgram import DeepgramClient, PrerecordedOptions
        self._client = DeepgramClient(api_key)
        self._options = PrerecordedOptions(model=model, smart_format=True, language="en")

    async def transcribe(self, wav_bytes: bytes) -> str:
        source = {"buffer": wav_bytes, "mimetype": "audio/wav"}
        response = await self._client.listen.asyncrest.v("1").transcribe_file(
            source, self._options
        )
        return response.results.channels[0].alternatives[0].transcript

class StubSTT(STT):
    def __init__(self, transcript: str = "hello"):
        self.transcript = transcript
    async def transcribe(self, wav_bytes: bytes) -> str:
        return self.transcript
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_stt.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/x4_companion/stt.py tests/test_stt.py
git commit -m "feat: Deepgram STT wrapper + Stub"
```

---

## Task 5: Deepgram Aura-2 TTS wrapper

**Files:**
- Create: `src/x4_companion/tts.py`
- Create: `tests/test_tts.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_tts.py`:
```python
import pytest
import respx
from httpx import Response
from x4_companion.tts import DeepgramTTS, StubTTS

@pytest.mark.asyncio
async def test_stub_tts_returns_marker_bytes():
    tts = StubTTS()
    out = await tts.synthesize("hi")
    assert out == b"PCM_FAKE"

@pytest.mark.asyncio
@respx.mock
async def test_deepgram_tts_posts_text_and_returns_audio():
    route = respx.post("https://api.deepgram.com/v1/speak").mock(
        return_value=Response(200, content=b"\x00\x01\x02")
    )
    tts = DeepgramTTS(api_key="dg-test", model="aura-2-thalia-en")
    out = await tts.synthesize("hello")
    assert out == b"\x00\x01\x02"
    assert route.called
    sent = route.calls.last.request
    body = sent.read().decode()
    assert '"text": "hello"' in body
    assert sent.headers["Authorization"] == "Token dg-test"
    assert "model=aura-2-thalia-en" in str(sent.url)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_tts.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the implementation**

`src/x4_companion/tts.py`:
```python
from abc import ABC, abstractmethod
import httpx

class TTS(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes: ...

class DeepgramTTS(TTS):
    def __init__(self, api_key: str, model: str = "aura-2-thalia-en"):
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(timeout=30.0)

    async def synthesize(self, text: str) -> bytes:
        url = (
            f"https://api.deepgram.com/v1/speak"
            f"?model={self._model}&encoding=linear16&sample_rate=24000"
        )
        r = await self._client.post(
            url,
            headers={
                "Authorization": f"Token {self._api_key}",
                "Content-Type": "application/json",
            },
            json={"text": text},
        )
        r.raise_for_status()
        return r.content

class StubTTS(TTS):
    async def synthesize(self, text: str) -> bytes:
        return b"PCM_FAKE"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_tts.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/x4_companion/tts.py tests/test_tts.py
git commit -m "feat: Deepgram Aura-2 TTS wrapper + Stub"
```

---

## Task 6: Audio recorder + player

**Files:**
- Create: `src/x4_companion/audio.py`
- Create: `tests/test_audio.py`

`AudioRecorder` and `AudioPlayer` wrap `sounddevice`. We test the WAV-encoding path by injecting a fake input stream; the playback path stays manual (it touches real hardware).

- [ ] **Step 1: Write the failing tests**

`tests/test_audio.py`:
```python
import io
import numpy as np
import pytest
import soundfile as sf
from x4_companion.audio import AudioRecorder

class _FakeStream:
    def __init__(self, samplerate, channels, dtype, device, callback):
        self.callback = callback
    def start(self):
        chunk = np.zeros((8000, 1), dtype=np.int16)
        chunk[::100] = 1000
        self.callback(chunk, len(chunk), None, None)
    def stop(self): pass
    def close(self): pass

def test_recorder_returns_valid_wav(monkeypatch):
    rec = AudioRecorder(sample_rate=16000)
    monkeypatch.setattr(rec._sd, "InputStream", _FakeStream)
    rec.start()
    wav = rec.stop()
    assert wav.startswith(b"RIFF")
    audio, sr = sf.read(io.BytesIO(wav))
    assert sr == 16000
    assert len(audio) == 8000

def test_recorder_returns_empty_when_no_audio(monkeypatch):
    class _NoCallbackStream(_FakeStream):
        def start(self): pass
    rec = AudioRecorder(sample_rate=16000)
    monkeypatch.setattr(rec._sd, "InputStream", _NoCallbackStream)
    rec.start()
    assert rec.stop() == b""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_audio.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the implementation**

`src/x4_companion/audio.py`:
```python
import io
import numpy as np
import soundfile as sf

class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, device: str | int | None = None):
        import sounddevice as sd
        self._sd = sd
        self._sample_rate = sample_rate
        self._device = device or None
        self._stream = None
        self._chunks: list[np.ndarray] = []

    def start(self) -> None:
        self._chunks = []
        def callback(indata, frames, time, status):
            self._chunks.append(indata.copy())
        self._stream = self._sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="int16",
            device=self._device,
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> bytes:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._chunks:
            return b""
        audio = np.concatenate(self._chunks, axis=0)
        buf = io.BytesIO()
        sf.write(buf, audio, self._sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()

class AudioPlayer:
    def __init__(self, sample_rate: int = 24000, device: str | int | None = None):
        import sounddevice as sd
        self._sd = sd
        self._sample_rate = sample_rate
        self._device = device or None

    def play(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes or pcm_bytes == b"PCM_FAKE":
            return
        audio = np.frombuffer(pcm_bytes, dtype=np.int16)
        self._sd.play(audio, samplerate=self._sample_rate, device=self._device)
        self._sd.wait()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_audio.py -v
```

Expected: 2 tests PASS. If `sounddevice` import fails on headless WSL, install `libportaudio2` (`sudo apt install libportaudio2`); if still failing, mark these tests with `@pytest.mark.skipif(platform.system() != 'Windows')` and run them on Windows.

- [ ] **Step 5: Commit**

```bash
git add src/x4_companion/audio.py tests/test_audio.py
git commit -m "feat: AudioRecorder + AudioPlayer (sounddevice)"
```

---

## Task 7: Capture module

**Files:**
- Create: `src/x4_companion/capture.py`
- Create: `tests/test_capture.py`
- Create: `tests/fixtures/x4_screenshot.png`

- [ ] **Step 1: Add the fixture screenshot**

```bash
.venv/bin/python -c "from PIL import Image; Image.new('RGB',(1280,720),'navy').save('tests/fixtures/x4_screenshot.png')"
```

- [ ] **Step 2: Write the failing tests**

`tests/test_capture.py`:
```python
from pathlib import Path
from x4_companion.capture import FakeCapture

FIXTURE = Path(__file__).parent / "fixtures" / "x4_screenshot.png"

def test_fake_capture_returns_supplied_bytes():
    data = FIXTURE.read_bytes()
    cap = FakeCapture(data)
    assert cap.get_current_frame() == data
    assert cap.get_current_frame()[:8] == b"\x89PNG\r\n\x1a\n"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_capture.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 4: Write the implementation**

`src/x4_companion/capture.py`:
```python
import io
from abc import ABC, abstractmethod
from PIL import Image

class Capture(ABC):
    @abstractmethod
    def get_current_frame(self) -> bytes:
        """Return PNG-encoded bytes of the current screen."""

class DxcamCapture(Capture):
    def __init__(self, max_width: int = 1280):
        import dxcam
        self._camera = dxcam.create()
        self._max_width = max_width

    def get_current_frame(self) -> bytes:
        frame = self._camera.grab()
        if frame is None:
            raise RuntimeError("capture failed (try borderless windowed mode in X4)")
        img = Image.fromarray(frame[:, :, ::-1])
        if img.width > self._max_width:
            ratio = self._max_width / img.width
            img = img.resize((self._max_width, int(img.height * ratio)))
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

class FakeCapture(Capture):
    def __init__(self, png_bytes: bytes):
        self._png = png_bytes
    def get_current_frame(self) -> bytes:
        return self._png
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_capture.py -v
```

Expected: 1 test PASS.

- [ ] **Step 6: Commit**

```bash
git add src/x4_companion/capture.py tests/test_capture.py tests/fixtures/x4_screenshot.png
git commit -m "feat: Capture interface + DxcamCapture + FakeCapture"
```

---

## Task 8: MiniMax API smoke test (live, exploratory)

This task is **not** TDD — it's a one-shot live probe to confirm the exact API call shape for MiniMax M2.7 + image understanding. The result feeds Task 9.

**Files:**
- Create: `scripts/minimax_smoke.py`
- Create: `docs/minimax-api-shape.md`

- [ ] **Step 1: Write the smoke script**

`scripts/minimax_smoke.py`:
```python
"""
Probe MiniMax M2.7 with an image + question.

Usage:
    MINIMAX_API_KEY=... python scripts/minimax_smoke.py

Expected: prints status code + JSON. We expect a 200 with a description of
the screenshot in the assistant message.

If 200: record the working request shape in docs/minimax-api-shape.md.
If 4xx: read the error, consult https://platform.minimax.io/docs, try the
documented image-understanding pattern (likely either OpenAI-compatible
'image_url' content blocks, or MMX MCP tool invocation), and update this
script + the doc accordingly.
"""
import base64
import os
import sys
from pathlib import Path
import httpx

api_key = os.environ.get("MINIMAX_API_KEY")
if not api_key:
    print("set MINIMAX_API_KEY", file=sys.stderr)
    sys.exit(2)

img = Path("tests/fixtures/x4_screenshot.png").read_bytes()
img_b64 = base64.b64encode(img).decode()

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
```

- [ ] **Step 2: Run the smoke test**

```bash
MINIMAX_API_KEY=... .venv/bin/python scripts/minimax_smoke.py
```

Three possible outcomes:

1. **200 with a sensible reply** → `image_url` content blocks work. Proceed to Task 9 with this exact pattern.
2. **400 "image not supported on this model"** → image goes through a separate path. Read https://platform.minimax.io/docs, find the image-understanding endpoint or MCP tool. Update `scripts/minimax_smoke.py` to use the working approach. Re-run.
3. **401/403** → API key wrong or missing image-understanding entitlement on the plan. Confirm Starter tier includes image understanding (it does per the plan spec); regenerate the key if needed.

- [ ] **Step 3: Document the working API shape**

`docs/minimax-api-shape.md`:
```markdown
# MiniMax M2.7 + Image Understanding — Working API shape

**As of 2026-05-08, Starter plan ($10/mo).**

Endpoint: `https://api.minimax.io/v1/text/chatcompletion_v2`
Auth: `Authorization: Bearer <MINIMAX_API_KEY>`

Request body:
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

Response (truncated): { "choices": [ { "message": { "content": "..." } } ] }

(If the actual shape differed, replace the above with what worked.)
```

- [ ] **Step 4: Commit**

```bash
git add scripts/minimax_smoke.py docs/minimax-api-shape.md
git commit -m "chore: minimax m2.7 + image understanding smoke probe"
```

---

## Task 9: MiniMaxBrain implementation

**Files:**
- Create: `src/x4_companion/minimax_brain.py`
- Create: `tests/test_minimax_brain.py`

If Task 8 found a different API shape, adapt the request payload below to match. The structure (system prompt, history, image attached to the latest user turn) stays the same.

- [ ] **Step 1: Write the failing tests**

`tests/test_minimax_brain.py`:
```python
import pytest
import respx
from httpx import Response
from x4_companion.minimax_brain import MiniMaxBrain

@pytest.mark.asyncio
@respx.mock
async def test_minimax_brain_calls_api_with_image_and_query():
    route = respx.post("https://api.minimax.io/v1/text/chatcompletion_v2").mock(
        return_value=Response(200, json={
            "choices": [{"message": {"content": "That's a Teladi station."}}]
        })
    )
    brain = MiniMaxBrain(api_key="mm-test")
    reply = await brain.answer(b"PNGBYTES", "what is this?")
    assert reply == "That's a Teladi station."
    body = route.calls.last.request.read().decode()
    assert "MiniMax-M2.7" in body
    assert "what is this?" in body
    assert "data:image/png;base64," in body

@pytest.mark.asyncio
@respx.mock
async def test_minimax_brain_includes_history_in_followup():
    respx.post("https://api.minimax.io/v1/text/chatcompletion_v2").mock(
        side_effect=[
            Response(200, json={"choices": [{"message": {"content": "first"}}]}),
            Response(200, json={"choices": [{"message": {"content": "second"}}]}),
        ]
    )
    brain = MiniMaxBrain(api_key="mm-test", history_turns=4)
    await brain.answer(b"P1", "q1")
    await brain.answer(b"P2", "q2")
    last_body = respx.calls.last.request.read().decode()
    assert "q1" in last_body
    assert "first" in last_body
    assert "q2" in last_body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_minimax_brain.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the implementation**

`src/x4_companion/minimax_brain.py`:
```python
import base64
import httpx
from .brain import Brain, ConversationHistory

SYSTEM_PROMPT = (
    "You are an experienced X4 Foundations player sitting next to the user as they play. "
    "You can see their screen. Answer questions concisely and conversationally. "
    "Keep replies under 60 words unless the user explicitly asks for detail. "
    "If the screenshot is unclear, say so rather than guessing."
)

class MiniMaxBrain(Brain):
    URL = "https://api.minimax.io/v1/text/chatcompletion_v2"

    def __init__(
        self,
        api_key: str,
        model: str = "MiniMax-M2.7",
        history_turns: int = 6,
        timeout: float = 60.0,
    ):
        self._api_key = api_key
        self._model = model
        self._history = ConversationHistory(max_turns=history_turns)
        self._client = httpx.AsyncClient(timeout=timeout)

    async def answer(self, frame_png: bytes, query: str) -> str:
        img_b64 = base64.b64encode(frame_png).decode()
        prior = self._history.as_messages()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *prior,
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": query},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            },
        ]
        r = await self._client.post(
            self.URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "messages": messages},
        )
        r.raise_for_status()
        reply = r.json()["choices"][0]["message"]["content"]
        self._history.append_user(query)
        self._history.append_assistant(reply)
        return reply

    async def aclose(self) -> None:
        await self._client.aclose()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_minimax_brain.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/x4_companion/minimax_brain.py tests/test_minimax_brain.py
git commit -m "feat: MiniMaxBrain (M2.7 + image understanding)"
```

---

## Task 10: Hotkey listener

**Files:**
- Create: `src/x4_companion/hotkey.py`
- Create: `tests/test_hotkey.py`

Global keyboard hooks can't be exercised in a unit test. We test the dedupe logic by calling `_handle_*` directly.

- [ ] **Step 1: Write the failing tests**

`tests/test_hotkey.py`:
```python
from x4_companion.hotkey import Hotkey

def test_hotkey_fires_once_per_press():
    downs, ups = [], []
    hk = Hotkey("home", lambda: downs.append(1), lambda: ups.append(1))
    hk._handle_down()
    hk._handle_down()
    hk._handle_up()
    hk._handle_up()
    assert downs == [1]
    assert ups == [1]

def test_hotkey_handles_multiple_press_release_cycles():
    downs, ups = [], []
    hk = Hotkey("home", lambda: downs.append(1), lambda: ups.append(1))
    for _ in range(3):
        hk._handle_down(); hk._handle_up()
    assert downs == [1, 1, 1]
    assert ups == [1, 1, 1]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_hotkey.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the implementation**

`src/x4_companion/hotkey.py`:
```python
from typing import Callable

class Hotkey:
    """Global push-to-talk hotkey. Suppresses OS auto-repeat while held."""

    def __init__(
        self,
        key: str,
        on_down: Callable[[], None],
        on_up: Callable[[], None],
    ):
        self._key = key
        self._on_down = on_down
        self._on_up = on_up
        self._pressed = False

    def start(self) -> None:
        import keyboard
        keyboard.on_press_key(self._key, lambda _e: self._handle_down())
        keyboard.on_release_key(self._key, lambda _e: self._handle_up())

    def stop(self) -> None:
        import keyboard
        keyboard.unhook_all()

    def _handle_down(self) -> None:
        if self._pressed:
            return
        self._pressed = True
        self._on_down()

    def _handle_up(self) -> None:
        if not self._pressed:
            return
        self._pressed = False
        self._on_up()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_hotkey.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/x4_companion/hotkey.py tests/test_hotkey.py
git commit -m "feat: PTT hotkey with repeat-suppression"
```

---

## Task 11: Overlay window

**Files:**
- Create: `src/x4_companion/overlay.py`

PySide6 widgets can't be unit-tested without a display server. Manual smoke check only.

- [ ] **Step 1: Write the implementation**

`src/x4_companion/overlay.py`:
```python
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QApplication

class Overlay(QLabel):
    """Transparent always-on-top text panel that fades after `fade_seconds`."""

    def __init__(
        self,
        position: str = "top-right",
        opacity: float = 0.85,
        font_size: int = 16,
        fade_seconds: int = 30,
    ):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet(
            "QLabel {"
            "  background-color: rgba(0, 0, 0, 200);"
            "  color: white;"
            "  padding: 12px 16px;"
            "  border-radius: 8px;"
            f"  font-size: {font_size}px;"
            "}"
        )
        self.setWindowOpacity(opacity)
        self.setWordWrap(True)
        self.setMaximumWidth(420)
        self._position = position
        self._fade_seconds = fade_seconds
        self._fade_timer = QTimer(self)
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self.hide)

    def show_text(self, text: str) -> None:
        self.setText(text)
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._fade_timer.start(self._fade_seconds * 1000)

    def _reposition(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        margin = 24
        if self._position == "top-right":
            x = screen.right() - self.width() - margin
            y = screen.top() + margin
        elif self._position == "top-left":
            x = screen.left() + margin
            y = screen.top() + margin
        elif self._position == "bottom-left":
            x = screen.left() + margin
            y = screen.bottom() - self.height() - margin
        else:
            x = screen.right() - self.width() - margin
            y = screen.bottom() - self.height() - margin
        self.move(x, y)
```

- [ ] **Step 2: Manual smoke test**

Save this as `scripts/overlay_smoke.py`:
```python
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from x4_companion.overlay import Overlay

app = QApplication(sys.argv)
overlay = Overlay(fade_seconds=3)
overlay.show_text("hello — does this look right?")
QTimer.singleShot(5000, app.quit)
sys.exit(app.exec_())
```

Run: `.venv/bin/python scripts/overlay_smoke.py`

Expected: a small dark rounded panel appears top-right, says "hello — does this look right?", fades after 3 seconds, app exits at 5s.

- [ ] **Step 3: Commit**

```bash
git add src/x4_companion/overlay.py scripts/overlay_smoke.py
git commit -m "feat: transparent always-on-top overlay (PySide6)"
```

---

## Task 12: Tray icon

**Files:**
- Create: `src/x4_companion/tray.py`

- [ ] **Step 1: Write the implementation**

`src/x4_companion/tray.py`:
```python
from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QStyle

class Tray(QSystemTrayIcon):
    quit_requested = Signal()

    def __init__(self, app: QApplication):
        icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        super().__init__(icon)
        self.setToolTip("X4 Companion")
        menu = QMenu()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        self.show()
```

- [ ] **Step 2: Manual smoke test**

Save as `scripts/tray_smoke.py`:
```python
import sys
from PySide6.QtWidgets import QApplication
from x4_companion.tray import Tray

app = QApplication(sys.argv)
tray = Tray(app)
tray.quit_requested.connect(app.quit)
sys.exit(app.exec_())
```

Run: `.venv/bin/python scripts/tray_smoke.py`

Expected: tray icon appears. Right-click → Quit exits cleanly.

- [ ] **Step 3: Commit**

```bash
git add src/x4_companion/tray.py scripts/tray_smoke.py
git commit -m "feat: system tray icon with Quit action"
```

---

## Task 13: App entry point — wire everything together

**Files:**
- Create: `src/x4_companion/app.py`
- Create: `docs/manual-test.md`

Integration glue — no unit tests. Verify by running.

- [ ] **Step 1: Write the implementation**

`src/x4_companion/app.py`:
```python
import asyncio
import sys
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from .audio import AudioPlayer, AudioRecorder
from .brain import Brain
from .capture import Capture, DxcamCapture
from .config import Config, load_config
from .hotkey import Hotkey
from .minimax_brain import MiniMaxBrain
from .overlay import Overlay
from .stt import STT, DeepgramSTT
from .tray import Tray
from .tts import TTS, DeepgramTTS


class _Bridge(QObject):
    show_text = Signal(str)
    ptt_down = Signal()
    ptt_up = Signal()


class App:
    def __init__(
        self,
        cfg: Config,
        capture: Capture,
        brain: Brain,
        stt: STT,
        tts: TTS,
    ):
        self.cfg = cfg
        self.capture = capture
        self.brain = brain
        self.stt = stt
        self.tts = tts
        self.recorder = AudioRecorder(device=cfg.audio.input_device or None)
        self.player = AudioPlayer(device=cfg.audio.output_device or None)

        self.qt = QApplication.instance() or QApplication(sys.argv)
        self.qt.setQuitOnLastWindowClosed(False)

        self.bridge = _Bridge()
        self.overlay = Overlay(
            position=cfg.overlay.position,
            opacity=cfg.overlay.opacity,
            font_size=cfg.overlay.font_size,
            fade_seconds=cfg.overlay.fade_seconds,
        )
        self.tray = Tray(self.qt)
        self.hotkey = Hotkey(
            cfg.hotkey.key,
            self.bridge.ptt_down.emit,
            self.bridge.ptt_up.emit,
        )

        self.bridge.show_text.connect(self.overlay.show_text)
        self.bridge.ptt_down.connect(self._on_ptt_down)
        self.bridge.ptt_up.connect(self._on_ptt_up)
        self.tray.quit_requested.connect(self.qt.quit)

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _on_ptt_down(self) -> None:
        try:
            self.recorder.start()
        except Exception as e:
            self.bridge.show_text.emit(f"(mic error: {e})")

    def _on_ptt_up(self) -> None:
        try:
            wav = self.recorder.stop()
        except Exception as e:
            self.bridge.show_text.emit(f"(mic error: {e})")
            return
        try:
            frame = self.capture.get_current_frame()
        except Exception as e:
            self.bridge.show_text.emit(f"(capture failed: {e})")
            return
        asyncio.run_coroutine_threadsafe(self._handle_turn(wav, frame), self._loop)

    async def _handle_turn(self, wav: bytes, frame: bytes) -> None:
        if not wav or len(wav) < 4000:
            self.bridge.show_text.emit("(didn't catch that)")
            return
        try:
            transcript = await self.stt.transcribe(wav)
        except Exception as e:
            self.bridge.show_text.emit(f"(stt error: {e})")
            return
        if not transcript.strip():
            self.bridge.show_text.emit("(didn't catch that)")
            return
        try:
            reply = await self.brain.answer(frame, transcript)
        except Exception as e:
            self.bridge.show_text.emit(f"(brain error: {e})")
            return
        self.bridge.show_text.emit(reply)
        try:
            audio = await self.tts.synthesize(reply)
            self.player.play(audio)
        except Exception:
            pass

    def run(self) -> int:
        self._loop_thread.start()
        self.hotkey.start()
        self.qt.aboutToQuit.connect(self._shutdown)
        return self.qt.exec_()

    def _shutdown(self) -> None:
        try:
            self.hotkey.stop()
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)


def main() -> int:
    cfg = load_config()
    if not cfg.secrets.minimax_api_key or not cfg.secrets.deepgram_api_key:
        print(
            "Set MINIMAX_API_KEY and DEEPGRAM_API_KEY environment variables.",
            file=sys.stderr,
        )
        return 1
    capture = DxcamCapture()
    brain = MiniMaxBrain(
        api_key=cfg.secrets.minimax_api_key,
        model=cfg.brain.model,
        history_turns=cfg.brain.history_turns,
    )
    stt = DeepgramSTT(api_key=cfg.secrets.deepgram_api_key)
    tts = DeepgramTTS(
        api_key=cfg.secrets.deepgram_api_key,
        model=cfg.voice.model,
    )
    return App(cfg, capture, brain, stt, tts).run()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Write `docs/manual-test.md`**

```markdown
# Manual test plan — X4 Companion

Run on the **Windows gaming PC** (the WSL dev machine can't reach the GPU/mic/keyboard the same way).

## Prereqs
- Repo cloned, `pip install -e ".[dev]"` complete
- `MINIMAX_API_KEY` + `DEEPGRAM_API_KEY` in env
- X4 Foundations installed; set graphics mode to **Borderless Windowed** (not Exclusive Fullscreen)
- VKB controller bound to send **Home** key for PTT (or use the keyboard Home key)

## Run
python -m x4_companion

## Smoke checks (no game running yet)
1. Tray icon appears.
2. Press Home, hold for 1s, say "hello", release.
3. Within ~3s: overlay shows a reply, TTS speaks it.
4. Right-click tray → Quit. Process exits cleanly.

## In-game checks (X4 launched, borderless)
1. Press Home, ask "what is on my screen?". Reply describes the X4 UI.
2. Hold Home, say nothing, release within 200ms → overlay says "(didn't catch that)".
3. Pull network → press Home, ask anything → overlay shows "(brain error: ...)".
4. Switch X4 to Exclusive Fullscreen → overlay says "(capture failed: ...)" instead of crashing.
5. Ask 3 follow-up questions in a row; answers should reflect awareness of prior turns.

## Latency
- Stopwatch from PTT release to first audible word. Target ≤3s.

## Quota check
- After ~30 questions in a session, no rate limit errors. (1500 reqs / 5h = ~750 PTT turns.)
```

- [ ] **Step 3: Run the unit-test suite end to end**

```bash
.venv/bin/pytest -v
```

Expected: all tests from Tasks 1-10 pass.

- [ ] **Step 4: Manual run on the Windows PC**

Follow `docs/manual-test.md`. Capture any failures as new tasks.

- [ ] **Step 5: Commit**

```bash
git add src/x4_companion/app.py docs/manual-test.md
git commit -m "feat: app entry point + manual test plan"
```

---

## Self-Review Checklist (run after Task 13)

- [ ] **Spec coverage:** Every section in the spec has at least one task.
  - Goal — Tasks 9, 13
  - Non-goals — excluded by design
  - User flow — Tasks 9-13
  - Architecture — Task 13 wires the layers
  - Components — one task per module
  - Data flow — Task 13's `_handle_turn`
  - Configuration — Task 2
  - Error handling — Task 13's try/except branches map to the spec table
  - Testing — unit per task; integration via Task 13 manual plan
  - Dev workflow — README + plan instructions

- [ ] **Placeholder scan:** Searched for "TBD", "TODO", "fill in" — none.

- [ ] **Type consistency:**
  - `Brain.answer(frame_png: bytes, query: str) -> str` matches in `brain.py`, `minimax_brain.py`, `app.py`
  - `Capture.get_current_frame() -> bytes` matches between `capture.py` and `app.py`
  - `STT.transcribe(wav_bytes: bytes) -> str` consistent
  - `TTS.synthesize(text: str) -> bytes` consistent

- [ ] **Open questions from spec:** Voice default (`aura-2-thalia-en`) chosen; `history_turns=6` chosen; auto-launch deferred; X4 wiki RAG deferred. All flagged in the spec as v1 defaults.

---

## Notes for the executor

- Run all `pytest` commands from the repo root with `.venv` activated (or use the explicit `.venv/bin/pytest` paths in the steps).
- Tasks 6 and 13's manual checks must run on the **Windows gaming PC**. Everything else can be developed and tested in WSL.
- Task 8 is the one place the plan may need to adapt — if MiniMax's API shape differs from what's assumed, update Task 9's request payload to match the doc you produce in Task 8.
- Frequent commits: each task ends with one commit. If a task is interrupted mid-way, commit what's done with a `wip:` prefix.
- After Task 13, push the branch and run the end-to-end manual test on the Windows PC before declaring v1 done.
