import pytest
from unittest.mock import AsyncMock, MagicMock
from x4_companion.stt import DeepgramSTT, StubSTT


@pytest.mark.asyncio
async def test_stub_stt_returns_canned_text():
    stt = StubSTT(transcript="hello world")
    assert await stt.transcribe(b"WAVBYTES") == "hello world"


@pytest.mark.asyncio
async def test_deepgram_stt_calls_sdk_with_request_bytes():
    stt = DeepgramSTT(api_key="dg-test")
    fake_response = MagicMock()
    fake_response.results.channels[0].alternatives[0].transcript = "what is this ship"
    transcribe_mock = AsyncMock(return_value=fake_response)
    stt._client.listen.v1.media.transcribe_file = transcribe_mock

    out = await stt.transcribe(b"FAKEWAV")

    assert out == "what is this ship"
    transcribe_mock.assert_called_once()
    kwargs = transcribe_mock.call_args.kwargs
    assert kwargs["request"] == b"FAKEWAV"
    assert kwargs["model"] == "nova-3"
    assert kwargs["smart_format"] is True
    assert kwargs["language"] == "en"
