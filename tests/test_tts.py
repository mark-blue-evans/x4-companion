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
    assert '"text":"hello"' in body
    assert sent.headers["Authorization"] == "Token dg-test"
    assert "model=aura-2-thalia-en" in str(sent.url)
