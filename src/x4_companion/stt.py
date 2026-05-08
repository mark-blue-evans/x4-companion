from abc import ABC, abstractmethod


class STT(ABC):
    @abstractmethod
    async def transcribe(self, wav_bytes: bytes) -> str: ...


class DeepgramSTT(STT):
    def __init__(self, api_key: str, model: str = "nova-3"):
        from deepgram import AsyncDeepgramClient
        self._client = AsyncDeepgramClient(api_key=api_key)
        self._model = model

    async def transcribe(self, wav_bytes: bytes) -> str:
        response = await self._client.listen.v1.media.transcribe_file(
            request=wav_bytes,
            model=self._model,
            smart_format=True,
            language="en",
        )
        return response.results.channels[0].alternatives[0].transcript


class StubSTT(STT):
    def __init__(self, transcript: str = "hello"):
        self.transcript = transcript

    async def transcribe(self, wav_bytes: bytes) -> str:
        return self.transcript
