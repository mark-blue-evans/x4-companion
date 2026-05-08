import pytest
from x4_companion.tts import DeepgramTTS, StubTTS


@pytest.mark.asyncio
async def test_stub_tts_yields_marker_bytes():
    tts = StubTTS()
    chunks = [chunk async for chunk in tts.stream("hi")]
    assert chunks == [b"PCM_FAKE"]


@pytest.mark.asyncio
async def test_stub_tts_yields_supplied_chunks():
    tts = StubTTS(chunks=[b"a", b"b", b"c"])
    chunks = [chunk async for chunk in tts.stream("hi")]
    assert chunks == [b"a", b"b", b"c"]


# --- DeepgramTTS WebSocket fakes -------------------------------------------
class _FakeFlushed:
    type = "Flushed"
    sequence_id = 0


class _FakeSocket:
    def __init__(self, messages):
        self._messages = messages
        self.sent_texts: list[str] = []
        self.flushed = False
        self.closed = False

    async def send_text(self, msg):
        self.sent_texts.append(msg.text)

    async def send_flush(self):
        self.flushed = True

    async def send_close(self):
        self.closed = True

    async def __aiter__(self):
        for m in self._messages:
            yield m


class _FakeConnectCM:
    def __init__(self, socket):
        self._socket = socket

    async def __aenter__(self):
        return self._socket

    async def __aexit__(self, *args):
        return False


class _FakeSpeakV1:
    def __init__(self, socket):
        self._socket = socket
        self.connect_kwargs: dict | None = None

    def connect(self, **kwargs):
        self.connect_kwargs = kwargs
        return _FakeConnectCM(self._socket)


class _FakeClient:
    def __init__(self, socket):
        self._speak_v1 = _FakeSpeakV1(socket)
        self.speak = type("speak", (), {"v1": self._speak_v1})()

    @property
    def speak_v1(self):
        return self._speak_v1


@pytest.mark.asyncio
async def test_deepgram_tts_streams_chunks_until_flushed(monkeypatch):
    socket = _FakeSocket([b"chunk1", b"chunk2", _FakeFlushed(), b"after_flushed_should_not_arrive"])
    fake_client = _FakeClient(socket)
    monkeypatch.setattr(
        "x4_companion.tts.AsyncDeepgramClient",
        lambda api_key=None: fake_client,
    )

    tts = DeepgramTTS(api_key="dg-test", model="aura-2-thalia-en", sample_rate=24000)
    chunks = []
    async for chunk in tts.stream("hello world"):
        chunks.append(chunk)

    assert chunks == [b"chunk1", b"chunk2"]
    assert socket.sent_texts == ["hello world"]
    assert socket.flushed
    assert socket.closed
    assert fake_client.speak_v1.connect_kwargs["model"] == "aura-2-thalia-en"
    assert fake_client.speak_v1.connect_kwargs["encoding"] == "linear16"
    assert fake_client.speak_v1.connect_kwargs["sample_rate"] == 24000


@pytest.mark.asyncio
async def test_deepgram_tts_handles_no_flushed_message(monkeypatch):
    # Server closes without ever sending Flushed — we should still get all chunks
    socket = _FakeSocket([b"a", b"b"])
    fake_client = _FakeClient(socket)
    monkeypatch.setattr(
        "x4_companion.tts.AsyncDeepgramClient",
        lambda api_key=None: fake_client,
    )

    tts = DeepgramTTS(api_key="dg-test")
    chunks = [c async for c in tts.stream("x")]
    assert chunks == [b"a", b"b"]
