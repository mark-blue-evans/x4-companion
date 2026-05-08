import pytest
from x4_companion.brain import ConversationHistory, StubBrain

def test_history_appends_alternating():
    h = ConversationHistory(max_turns=3)
    h.append_user("q1"); h.append_assistant("a1")
    h.append_user("q2"); h.append_assistant("a2")
    msgs = h.as_messages()
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert msgs[2]["content"] == "q2"

def test_history_drops_oldest_when_full():
    h = ConversationHistory(max_turns=2)
    for i in range(4):
        h.append_user(f"q{i}"); h.append_assistant(f"a{i}")
    msgs = h.as_messages()
    assert len(msgs) == 4
    assert msgs[0]["content"] == "q2"
    assert msgs[-1]["content"] == "a3"

@pytest.mark.asyncio
async def test_stub_brain_returns_canned_reply_and_records_inputs():
    b = StubBrain(reply="canned")
    out = await b.answer(b"PNGBYTES", "what is this?")
    assert out.text == "canned"
    assert out.pending_action is None
    assert b.last_query == "what is this?"
    assert b.last_frame == b"PNGBYTES"
