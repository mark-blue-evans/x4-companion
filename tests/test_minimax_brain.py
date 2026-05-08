import pytest
import respx
from httpx import Response
from x4_companion.minimax_brain import MiniMaxBrain

VLM_URL = "https://api.minimax.io/v1/coding_plan/vlm"


@pytest.mark.asyncio
@respx.mock
async def test_minimax_brain_calls_api_with_image_and_query():
    route = respx.post(VLM_URL).mock(
        return_value=Response(200, json={"content": "That's a Teladi station."})
    )
    brain = MiniMaxBrain(api_key="mm-test")
    reply = await brain.answer(b"PNGBYTES", "what is this?")
    assert reply == "That's a Teladi station."
    body = route.calls.last.request.read().decode()
    assert "what is this?" in body
    assert "data:image/png;base64," in body


@pytest.mark.asyncio
@respx.mock
async def test_minimax_brain_includes_history_in_followup():
    respx.post(VLM_URL).mock(
        side_effect=[
            Response(200, json={"content": "first"}),
            Response(200, json={"content": "second"}),
        ]
    )
    brain = MiniMaxBrain(api_key="mm-test", history_turns=4)
    await brain.answer(b"P1", "q1")
    await brain.answer(b"P2", "q2")
    last_body = respx.calls.last.request.read().decode()
    assert "q1" in last_body
    assert "first" in last_body
    assert "q2" in last_body


@pytest.mark.asyncio
@respx.mock
async def test_minimax_brain_injects_vkb_bindings_when_provided():
    respx.post(VLM_URL).mock(
        return_value=Response(200, json={"content": "ok"})
    )
    bindings = "A4 HAT Press -- Deselects target"
    brain = MiniMaxBrain(api_key="mm-test", vkb_bindings=bindings)
    await brain.answer(b"P", "how do I deselect?")
    body = respx.calls.last.request.read().decode()
    assert "VKB Gladiator" in body
    assert "Deselects target" in body


@pytest.mark.asyncio
@respx.mock
async def test_minimax_brain_omits_vkb_section_when_not_provided():
    respx.post(VLM_URL).mock(
        return_value=Response(200, json={"content": "ok"})
    )
    brain = MiniMaxBrain(api_key="mm-test")
    await brain.answer(b"P", "anything")
    body = respx.calls.last.request.read().decode()
    assert "VKB" not in body
