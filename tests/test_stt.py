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
    stt._client.listen.v1.media.transcribe_file = transcribe_mock
    out = await stt.transcribe(b"FAKEWAV")
    assert out == "what is this ship"
    args, kwargs = transcribe_mock.call_args
    assert args[0]["buffer"] == b"FAKEWAV"
    assert args[0]["mimetype"] == "audio/wav"
