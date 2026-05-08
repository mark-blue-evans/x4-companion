import pytest
import respx
from httpx import Response
from x4_companion.minimax_brain import MiniMaxBrain

@pytest.mark.asyncio
@respx.mock
async def test_minimax_brain_calls_api_with_image_and_query():
    route = respx.post("https://api.minimax.io/v1/text/chatcompletion_v2").mock(
        return_value=Response(200, json={
            "choices": [{"message": {"content": "That's a Teladi station."}}]
        })
    )
    brain = MiniMaxBrain(api_key="mm-test")
    reply = await brain.answer(b"PNGBYTES", "what is this?")
    assert reply == "That's a Teladi station."
    body = route.calls.last.request.read().decode()
    assert "MiniMax-M2.7" in body
    assert "what is this?" in body
    assert "data:image/png;base64," in body

@pytest.mark.asyncio
@respx.mock
async def test_minimax_brain_includes_history_in_followup():
    respx.post("https://api.minimax.io/v1/text/chatcompletion_v2").mock(
        side_effect=[
            Response(200, json={"choices": [{"message": {"content": "first"}}]}),
            Response(200, json={"choices": [{"message": {"content": "second"}}]}),
        ]
    )
    brain = MiniMaxBrain(api_key="mm-test", history_turns=4)
    await brain.answer(b"P1", "q1")
    await brain.answer(b"P2", "q2")
    last_body = respx.calls.last.request.read().decode()
    assert "q1" in last_body
    assert "first" in last_body
    assert "q2" in last_body
