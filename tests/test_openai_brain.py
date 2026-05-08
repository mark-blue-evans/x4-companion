import pytest

from x4_companion.openai_brain import OpenAIBrain


class _FakeResponse:
    def __init__(self, text: str = "ok"):
        self.output_text = text


class _FakeResponses:
    def __init__(self):
        self.calls: list[dict] = []
        self._reply = "stub reply"

    def set_reply(self, text: str) -> None:
        self._reply = text

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self._reply)


class _FakeClient:
    def __init__(self):
        self.responses = _FakeResponses()
        self.closed = False

    async def close(self):
        self.closed = True


@pytest.fixture
def fake_client(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(
        "x4_companion.openai_brain.AsyncOpenAI",
        lambda **kwargs: client,
    )
    return client


@pytest.mark.asyncio
async def test_openai_brain_calls_responses_api_with_image_and_query(fake_client):
    fake_client.responses.set_reply("That's a Teladi station.")
    brain = OpenAIBrain(api_key="oa-test", web_search=False)
    reply = await brain.answer(b"\xff\xd8\xff\xe0BYTES", "what is this?")
    assert reply == "That's a Teladi station."

    call = fake_client.responses.calls[-1]
    assert call["model"] == "gpt-5-nano"
    assert "tools" not in call
    user_msg = call["input"][-1]
    assert user_msg["role"] == "user"
    text_block, image_block = user_msg["content"]
    assert text_block == {"type": "input_text", "text": "what is this?"}
    assert image_block["type"] == "input_image"
    assert image_block["image_url"].startswith("data:image/jpeg;base64,")


@pytest.mark.asyncio
async def test_openai_brain_includes_web_search_tool_when_enabled(fake_client):
    brain = OpenAIBrain(api_key="oa-test", web_search=True)
    await brain.answer(b"PNG_BYTES", "anything")
    call = fake_client.responses.calls[-1]
    assert call["tools"] == [{"type": "web_search_preview"}]


@pytest.mark.asyncio
async def test_openai_brain_includes_history_in_followup(fake_client):
    fake_client.responses.set_reply("first")
    brain = OpenAIBrain(api_key="oa-test", web_search=False, history_turns=4)
    await brain.answer(b"P1", "q1")

    fake_client.responses.set_reply("second")
    await brain.answer(b"P2", "q2")

    second_call_input = fake_client.responses.calls[-1]["input"]
    roles_and_text = [
        (m["role"], m["content"] if isinstance(m["content"], str) else None)
        for m in second_call_input
    ]
    assert ("user", "q1") in roles_and_text
    assert ("assistant", "first") in roles_and_text


@pytest.mark.asyncio
async def test_openai_brain_injects_vkb_bindings_when_provided(fake_client):
    bindings = "A4 HAT Press -- Deselects target"
    brain = OpenAIBrain(api_key="oa-test", vkb_bindings=bindings, web_search=False)
    await brain.answer(b"P", "how do I deselect?")
    system_msg = fake_client.responses.calls[-1]["input"][0]
    assert system_msg["role"] == "system"
    assert "VKB Gladiator" in system_msg["content"]
    assert "Deselects target" in system_msg["content"]


@pytest.mark.asyncio
async def test_openai_brain_omits_vkb_section_when_not_provided(fake_client):
    brain = OpenAIBrain(api_key="oa-test", web_search=False)
    await brain.answer(b"P", "anything")
    system_msg = fake_client.responses.calls[-1]["input"][0]
    assert "VKB" not in system_msg["content"]


@pytest.mark.asyncio
async def test_openai_brain_includes_today_date_in_system(fake_client):
    brain = OpenAIBrain(api_key="oa-test", web_search=False)
    await brain.answer(b"P", "anything")
    system_msg = fake_client.responses.calls[-1]["input"][0]
    assert "Today is" in system_msg["content"]
