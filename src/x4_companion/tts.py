from abc import ABC, abstractmethod
from typing import AsyncIterator

from deepgram import AsyncDeepgramClient
from deepgram.speak.v1.types import SpeakV1Text


class TTS(ABC):
    @abstractmethod
    def stream(self, text: str) -> AsyncIterator[bytes]:
        """Yield raw PCM audio chunks (linear16, mono) as they arrive."""


class DeepgramTTS(TTS):
    def __init__(
        self,
        api_key: str,
        model: str = "aura-2-thalia-en",
        sample_rate: int = 24000,
    ):
        self._model = model
        self._sample_rate = sample_rate
        self._client = AsyncDeepgramClient(api_key=api_key)

    async def stream(self, text: str) -> AsyncIterator[bytes]:
        async with self._client.speak.v1.connect(
            model=self._model,
            encoding="linear16",
            sample_rate=self._sample_rate,
        ) as ws:
            await ws.send_text(SpeakV1Text(text=text))
            await ws.send_flush()
            async for msg in ws:
                if isinstance(msg, bytes):
                    yield msg
                elif getattr(msg, "type", None) == "Flushed":
                    break
            await ws.send_close()


class StubTTS(TTS):
    def __init__(self, chunks: list[bytes] | None = None):
        self._chunks = chunks or [b"PCM_FAKE"]

    async def stream(self, text: str) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk
