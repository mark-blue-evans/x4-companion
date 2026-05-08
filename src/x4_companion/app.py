import asyncio
import logging
import os
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from .audio import AudioPlayer, AudioRecorder
from .brain import Brain
from .capture import Capture, DxcamCapture
from .config import Config, load_config
from .hotkey import Hotkey
from .minimax_brain import MiniMaxBrain
from .openai_brain import OpenAIBrain
from .overlay import Overlay
from .stt import STT, DeepgramSTT
from .tray import Tray
from .tts import TTS, DeepgramTTS

BRAIN_OPTIONS: list[tuple[str, str]] = [
    ("openai", "OpenAI (GPT-5 nano)"),
    ("minimax", "MiniMax (M2.7)"),
]

VKB_BINDINGS_PATH = Path(__file__).parent / "data" / "vkb_bindings.md"


def _strip_markdown(text: str) -> str:
    return text.replace("**", "").replace("`", "").replace("*", "")


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader. Existing env vars take precedence.

    utf-8-sig strips an optional BOM so editors/PowerShell that prepend one
    don't corrupt the first key.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


SESSION_LOG_PATH = Path.cwd() / "session.log"
log = logging.getLogger("x4_companion")


def _setup_logging() -> None:
    log.setLevel(logging.INFO)
    log.handlers.clear()
    handler = logging.FileHandler(str(SESSION_LOG_PATH), mode="w", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s.%(msecs)03d %(message)s", datefmt="%H:%M:%S")
    )
    log.addHandler(handler)
    log.propagate = False


def _load_vkb_bindings() -> str | None:
    if not VKB_BINDINGS_PATH.exists():
        return None
    return VKB_BINDINGS_PATH.read_text()


class _Bridge(QObject):
    show_text = Signal(str)
    ptt_down = Signal()
    ptt_up = Signal()


class App:
    def __init__(
        self,
        cfg: Config,
        capture: Capture,
        brains: dict[str, Brain],
        active_brain: str,
        stt: STT,
        tts: TTS,
    ):
        self.cfg = cfg
        self.capture = capture
        self.brains = brains
        self.active_brain = active_brain
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
        self.tray = Tray(
            self.qt,
            brain_options=[(k, label) for k, label in BRAIN_OPTIONS if k in brains],
            active_brain=active_brain,
        )
        self.hotkey = Hotkey(
            cfg.hotkey.key,
            self.bridge.ptt_down.emit,
            self.bridge.ptt_up.emit,
        )

        self.bridge.show_text.connect(self.overlay.show_text)
        self.bridge.ptt_down.connect(self._on_ptt_down)
        self.bridge.ptt_up.connect(self._on_ptt_up)
        self.tray.quit_requested.connect(self.qt.quit)
        self.tray.brain_changed.connect(self._on_brain_changed)

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._busy = False
        self._playback_task: asyncio.Task | None = None

    @property
    def brain(self) -> Brain:
        return self.brains[self.active_brain]

    def _on_brain_changed(self, key: str) -> None:
        if key in self.brains and key != self.active_brain:
            self.active_brain = key
            label = dict(BRAIN_OPTIONS).get(key, key)
            self.bridge.show_text.emit(f"(switched to {label})")
            log.info("brain switched to %s", key)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _on_ptt_down(self) -> None:
        if self._busy:
            self.bridge.show_text.emit("(still thinking...)")
            log.info("ptt_down ignored — still busy")
            return
        try:
            self.recorder.start()
        except Exception as e:
            self.bridge.show_text.emit(f"(mic error: {e})")
            log.error("mic error on ptt_down: %s", e)
            return
        self.bridge.show_text.emit("(listening...)")
        log.info("ptt_down — recording started")

    def _on_ptt_up(self) -> None:
        if self._busy:
            return
        try:
            wav = self.recorder.stop()
        except Exception as e:
            self.bridge.show_text.emit(f"(mic error: {e})")
            log.error("mic error on ptt_up: %s", e)
            return
        t_capture = time.monotonic()
        try:
            frame = self.capture.get_current_frame()
        except Exception as e:
            self.bridge.show_text.emit(f"(capture failed: {e})")
            log.error("capture failed: %s", e)
            return
        log.info(
            "ptt_up — wav=%dB, frame=%dB (capture=%.2fs)",
            len(wav),
            len(frame),
            time.monotonic() - t_capture,
        )
        self._busy = True
        self.bridge.show_text.emit("(thinking...)")
        if self._playback_task and not self._playback_task.done():
            self._loop.call_soon_threadsafe(self._playback_task.cancel)
        asyncio.run_coroutine_threadsafe(self._handle_turn(wav, frame), self._loop)

    async def _handle_turn(self, wav: bytes, frame: bytes) -> None:
        t_turn = time.monotonic()
        try:
            if not wav or len(wav) < 4000:
                self.bridge.show_text.emit("(didn't catch that)")
                log.info("rejected — wav too short (%dB)", len(wav))
                return
            t = time.monotonic()
            try:
                transcript = await self.stt.transcribe(wav)
            except Exception as e:
                self.bridge.show_text.emit(f"(stt error: {e})")
                log.error("stt error: %s", e)
                return
            log.info("stt %.2fs — %r", time.monotonic() - t, transcript)
            if not transcript.strip():
                self.bridge.show_text.emit("(didn't catch that)")
                return
            t = time.monotonic()
            try:
                reply = await self.brain.answer(frame, transcript)
            except Exception as e:
                self.bridge.show_text.emit(f"(brain error: {e})")
                log.error("brain (%s) error: %s", self.active_brain, e)
                return
            log.info(
                "brain %s %.2fs — %r",
                self.active_brain,
                time.monotonic() - t,
                reply[:120] + ("..." if len(reply) > 120 else ""),
            )
            self.bridge.show_text.emit(reply)
            self._playback_task = asyncio.create_task(
                self._stream_audio(_strip_markdown(reply), t_turn)
            )
        finally:
            self._busy = False
            log.info("turn done in %.2fs (audio still streaming)", time.monotonic() - t_turn)

    async def _stream_audio(self, text: str, t_turn: float) -> None:
        if not text:
            return
        loop = asyncio.get_event_loop()
        try:
            playback = await loop.run_in_executor(None, self.player.open_stream)
        except Exception as e:
            log.error("playback open failed: %s", e)
            return
        first_chunk_at: float | None = None
        try:
            async for chunk in self.tts.stream(text):
                if first_chunk_at is None:
                    first_chunk_at = time.monotonic()
                    log.info(
                        "tts first chunk at %.2fs from ptt_up",
                        first_chunk_at - t_turn,
                    )
                await loop.run_in_executor(None, playback.write, chunk)
        except asyncio.CancelledError:
            log.info("playback cancelled (new turn started)")
            raise
        except Exception as e:
            log.error("tts stream error: %s", e)
        finally:
            await loop.run_in_executor(None, playback.close)
            if first_chunk_at is not None:
                log.info("audio done at %.2fs from ptt_up", time.monotonic() - t_turn)

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
        if self._playback_task and not self._playback_task.done():
            self._loop.call_soon_threadsafe(self._playback_task.cancel)
        clients: list = list(self.brains.values()) + [self.tts]
        for client in clients:
            aclose = getattr(client, "aclose", None)
            if aclose is None:
                continue
            try:
                asyncio.run_coroutine_threadsafe(aclose(), self._loop).result(timeout=5)
            except Exception:
                pass
        self._loop.call_soon_threadsafe(self._loop.stop)


def main() -> int:
    _setup_logging()
    _load_dotenv(Path.cwd() / ".env")
    log.info("=== x4-companion start ===")
    cfg = load_config()
    if not cfg.secrets.deepgram_api_key:
        print("Set DEEPGRAM_API_KEY (system env var or .env file).", file=sys.stderr)
        return 1

    vkb = _load_vkb_bindings()
    brains: dict[str, Brain] = {}
    if cfg.secrets.openai_api_key:
        brains["openai"] = OpenAIBrain(
            api_key=cfg.secrets.openai_api_key,
            model=cfg.brain.openai_model,
            history_turns=cfg.brain.history_turns,
            vkb_bindings=vkb,
            web_search=cfg.brain.web_search,
            reasoning_effort=cfg.brain.openai_reasoning_effort,
        )
    if cfg.secrets.minimax_api_key:
        brains["minimax"] = MiniMaxBrain(
            api_key=cfg.secrets.minimax_api_key,
            history_turns=cfg.brain.history_turns,
            vkb_bindings=vkb,
        )
    if not brains:
        print(
            "Set at least one of OPENAI_API_KEY or MINIMAX_API_KEY in .env.",
            file=sys.stderr,
        )
        return 1

    active = cfg.brain.default
    if active not in brains:
        active = next(iter(brains))
    log.info("brains loaded: %s; active=%s", list(brains.keys()), active)

    capture = DxcamCapture()
    stt = DeepgramSTT(api_key=cfg.secrets.deepgram_api_key)
    tts = DeepgramTTS(
        api_key=cfg.secrets.deepgram_api_key,
        model=cfg.voice.model,
    )
    return App(cfg, capture, brains, active, stt, tts).run()


if __name__ == "__main__":
    sys.exit(main())
