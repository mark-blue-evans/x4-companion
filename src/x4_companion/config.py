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
    default: str = "openai"
    model: str = "MiniMax-M2.7"
    openai_model: str = "gpt-5-nano"
    openai_reasoning_effort: str = "minimal"
    image_understanding: bool = True
    history_turns: int = 6
    web_search: bool = False

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
    openai_api_key: str = ""

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
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        ),
    )
