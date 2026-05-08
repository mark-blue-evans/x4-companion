import base64
import datetime
from typing import Any

from openai import AsyncOpenAI

from .brain import Brain, ConversationHistory
from .minimax_brain import BASE_SYSTEM_PROMPT, VKB_PREAMBLE


class OpenAIBrain(Brain):
    """Vision + web-search brain backed by OpenAI's Responses API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5-nano",
        history_turns: int = 6,
        timeout: float = 60.0,
        vkb_bindings: str | None = None,
        web_search: bool = False,
        reasoning_effort: str = "minimal",
    ):
        self._model = model
        self._history = ConversationHistory(max_turns=history_turns)
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self._web_search = web_search
        self._reasoning_effort = reasoning_effort
        prompt = BASE_SYSTEM_PROMPT
        if vkb_bindings:
            prompt += VKB_PREAMBLE + vkb_bindings
        self._system_prompt = prompt

    async def answer(self, frame: bytes, query: str) -> str:
        img_b64 = base64.b64encode(frame).decode()
        mime = "image/jpeg" if frame[:3] == b"\xff\xd8\xff" else "image/png"
        now = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M %Z").strip()
        system = f"{self._system_prompt}\n\nToday is {now}."

        messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for turn in self._history.as_messages():
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": query},
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime};base64,{img_b64}",
                    },
                ],
            }
        )

        kwargs: dict[str, Any] = {"model": self._model, "input": messages}
        if self._reasoning_effort:
            kwargs["reasoning"] = {"effort": self._reasoning_effort}
        if self._web_search:
            kwargs["tools"] = [{"type": "web_search_preview"}]

        response = await self._client.responses.create(**kwargs)
        reply = response.output_text or ""
        self._history.append_user(query)
        self._history.append_assistant(reply)
        return reply

    async def aclose(self) -> None:
        try:
            await self._client.close()
        except Exception:
            pass
