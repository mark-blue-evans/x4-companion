import asyncio
import os
import sys
import threading
from pathlib import Path

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

VKB_BINDINGS_PATH = Path(__file__).parent / "data" / "vkb_bindings.md"


def _strip_markdown(text: str) -> str:
    return text.replace("**", "").replace("`", "").replace("*", "")


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader. Existing env vars take precedence."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


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
        self._busy = False

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _on_ptt_down(self) -> None:
        if self._busy:
            self.bridge.show_text.emit("(still thinking...)")
            return
        try:
            self.recorder.start()
        except Exception as e:
            self.bridge.show_text.emit(f"(mic error: {e})")
            return
        self.bridge.show_text.emit("(listening...)")

    def _on_ptt_up(self) -> None:
        if self._busy:
            return
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
        self._busy = True
        self.bridge.show_text.emit("(thinking...)")
        asyncio.run_coroutine_threadsafe(self._handle_turn(wav, frame), self._loop)

    async def _handle_turn(self, wav: bytes, frame: bytes) -> None:
        try:
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
                audio = await self.tts.synthesize(_strip_markdown(reply))
                await asyncio.get_event_loop().run_in_executor(None, self.player.play, audio)
            except Exception:
                pass
        finally:
            self._busy = False

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
        for client in (self.brain, self.tts):
            aclose = getattr(client, "aclose", None)
            if aclose is None:
                continue
            try:
                asyncio.run_coroutine_threadsafe(aclose(), self._loop).result(timeout=5)
            except Exception:
                pass
        self._loop.call_soon_threadsafe(self._loop.stop)


def main() -> int:
    _load_dotenv(Path.cwd() / ".env")
    cfg = load_config()
    if not cfg.secrets.minimax_api_key or not cfg.secrets.deepgram_api_key:
        print(
            "Set MINIMAX_API_KEY and DEEPGRAM_API_KEY (system env vars or .env file).",
            file=sys.stderr,
        )
        return 1
    capture = DxcamCapture()
    brain = MiniMaxBrain(
        api_key=cfg.secrets.minimax_api_key,
        history_turns=cfg.brain.history_turns,
        vkb_bindings=_load_vkb_bindings(),
    )
    stt = DeepgramSTT(api_key=cfg.secrets.deepgram_api_key)
    tts = DeepgramTTS(
        api_key=cfg.secrets.deepgram_api_key,
        model=cfg.voice.model,
    )
    return App(cfg, capture, brain, stt, tts).run()


if __name__ == "__main__":
    sys.exit(main())
