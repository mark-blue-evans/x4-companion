from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str
    content: str


@dataclass(frozen=True)
class ProposedAction:
    """Keyboard action a brain proposes to perform in X4. The app stores this
    as pending until the user confirms with a phrase like 'go' or 'do it'."""
    name: str
    keys: tuple[str, ...]
    explanation: str = ""


@dataclass
class BrainReply:
    text: str
    pending_action: ProposedAction | None = None


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
    async def answer(self, frame_png: bytes, query: str) -> BrainReply: ...


class StubBrain(Brain):
    def __init__(self, reply: str = "stub reply", action: ProposedAction | None = None):
        self.reply = reply
        self.action = action
        self.last_frame: bytes | None = None
        self.last_query: str | None = None

    async def answer(self, frame_png: bytes, query: str) -> BrainReply:
        self.last_frame = frame_png
        self.last_query = query
        return BrainReply(text=self.reply, pending_action=self.action)
