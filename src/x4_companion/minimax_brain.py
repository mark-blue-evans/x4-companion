import base64
import datetime
import httpx
from .brain import Brain, BrainReply, ConversationHistory

BASE_SYSTEM_PROMPT = (
    "You are an experienced X4 Foundations player sitting next to the user "
    "as they play. EVERY user message includes a fresh screenshot of their "
    "screen — you can see exactly what they see. When the user asks ANY "
    "visual question ('what mode am I in', 'what is that', 'where am I', "
    "'is this a station'), look at the screenshot first and answer from "
    "what's visible. Do NOT say 'I can't see your screen' — you can.\n"
    "\n"
    "X4 visual cues to recognize on screen:\n"
    "- Ship cockpit / HUD tinted PINK or red overlay → Long Range Scan "
    "Mode (LRS) is active.\n"
    "- Ship cockpit / HUD tinted BLUE or cyan overlay → Short Range Scan "
    "Mode is active.\n"
    "- Normal cockpit colors with no overlay → Default flight mode.\n"
    "- Travel-mode HUD (speed streaks, blue cruise overlay) → Travel Mode "
    "engaged.\n"
    "- Red target outlines/brackets → hostile.\n"
    "- White/grey target brackets → neutral or unknown.\n"
    "- Yellow or green → friendly / your own.\n"
    "- A docking ring icon over a target → can dock there.\n"
    "- Compass / map at the top center → standard cockpit HUD.\n"
    "\n"
    "Reply ULTRA-CONCISELY: 1-2 short sentences, ideally under 20 words. "
    "No preambles like 'Sure!' or 'Of course!', no recap of the question. "
    "Only go longer (still under 40 words) if the user explicitly asks "
    "you to 'explain more' or 'go into detail'. If the screenshot is "
    "genuinely unclear or doesn't show the answer, say so in one "
    "sentence. Plain text only — no markdown, asterisks, or bullet lists. "
    "Write the way you'd speak."
)

VKB_PREAMBLE = (
    "\n\nThe user is playing on a VKB Gladiator NTX EVO dual-stick setup using "
    "the codejnki/x4_vkb keybinding profile. When the user asks how to do "
    "something, prefer telling them which physical button on the VKB sticks "
    "to press (using the bindings below) over generic keyboard shortcuts. "
    "If the action is not bound on the sticks, give the keyboard shortcut.\n\n"
    "--- VKB BINDINGS (codejnki/x4_vkb) ---\n"
)

class MiniMaxBrain(Brain):
    URL = "https://api.minimax.io/v1/coding_plan/vlm"

    def __init__(
        self,
        api_key: str,
        history_turns: int = 6,
        timeout: float = 60.0,
        vkb_bindings: str | None = None,
    ):
        self._api_key = api_key
        self._history = ConversationHistory(max_turns=history_turns)
        self._client = httpx.AsyncClient(timeout=timeout)
        prompt = BASE_SYSTEM_PROMPT
        if vkb_bindings:
            prompt += VKB_PREAMBLE + vkb_bindings
        self._system_prompt = prompt

    async def answer(self, frame: bytes, query: str) -> BrainReply:
        img_b64 = base64.b64encode(frame).decode()
        mime = "image/jpeg" if frame[:3] == b"\xff\xd8\xff" else "image/png"
        now = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M %Z").strip()
        parts = [self._system_prompt, f"Today is {now}."]
        history_text = self._history.as_text()
        if history_text:
            parts.append(history_text)
        parts.append(f"user: {query}")
        prompt = "\n\n".join(parts)
        r = await self._client.post(
            self.URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"prompt": prompt, "image_url": f"data:{mime};base64,{img_b64}"},
        )
        r.raise_for_status()
        reply = r.json()["content"]
        self._history.append_user(query)
        self._history.append_assistant(reply)
        return BrainReply(text=reply)

    async def aclose(self) -> None:
        await self._client.aclose()
