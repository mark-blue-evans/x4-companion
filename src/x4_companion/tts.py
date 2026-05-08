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
