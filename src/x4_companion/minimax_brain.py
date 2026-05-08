import base64
import httpx
from .brain import Brain, ConversationHistory

SYSTEM_PROMPT = (
    "You are an experienced X4 Foundations player sitting next to the user as they play. "
    "You can see their screen. Answer questions concisely and conversationally. "
    "Keep replies under 60 words unless the user explicitly asks for detail. "
    "If the screenshot is unclear, say so rather than guessing."
)

class MiniMaxBrain(Brain):
    URL = "https://api.minimax.io/v1/text/chatcompletion_v2"

    def __init__(
        self,
        api_key: str,
        model: str = "MiniMax-M2.7",
        history_turns: int = 6,
        timeout: float = 60.0,
    ):
        self._api_key = api_key
        self._model = model
        self._history = ConversationHistory(max_turns=history_turns)
        self._client = httpx.AsyncClient(timeout=timeout)

    async def answer(self, frame_png: bytes, query: str) -> str:
        img_b64 = base64.b64encode(frame_png).decode()
        prior = self._history.as_messages()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *prior,
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": query},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            },
        ]
        r = await self._client.post(
            self.URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "messages": messages},
        )
        r.raise_for_status()
        reply = r.json()["choices"][0]["message"]["content"]
        self._history.append_user(query)
        self._history.append_assistant(reply)
        return reply

    async def aclose(self) -> None:
        await self._client.aclose()
