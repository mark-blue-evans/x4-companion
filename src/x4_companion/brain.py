from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass

@dataclass
class Turn:
    role: str
    content: str

class ConversationHistory:
    def __init__(self, max_turns: int = 6):
        self._turns: deque[Turn] = deque(maxlen=max_turns * 2)

    def append_user(self, text: str) -> None:
        self._turns.append(Turn("user", text))

    def append_assistant(self, text: str) -> None:
        self._turns.append(Turn("assistant", text))

    def as_messages(self) -> list[dict]:
        return [{"role": t.role, "content": t.content} for t in self._turns]

    def as_text(self) -> str:
        return "\n".join(f"{t.role}: {t.content}" for t in self._turns)

class Brain(ABC):
    @abstractmethod
    async def answer(self, frame_png: bytes, query: str) -> str: ...

class StubBrain(Brain):
    def __init__(self, reply: str = "stub reply"):
        self.reply = reply
        self.last_frame: bytes | None = None
        self.last_query: str | None = None

    async def answer(self, frame_png: bytes, query: str) -> str:
        self.last_frame = frame_png
        self.last_query = query
        return self.reply
