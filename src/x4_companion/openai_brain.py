import base64
import datetime
import json
from typing import Any

from openai import AsyncOpenAI

from .brain import Brain, BrainReply, ConversationHistory, ProposedAction
from .minimax_brain import BASE_SYSTEM_PROMPT, VKB_PREAMBLE

KEYBOARD_DEFAULTS_PREAMBLE = (
    "\n\n--- X4 KEYBOARD BINDINGS (used for execution — ALWAYS use these,"
    " never VKB button names) ---\n"
)

ACTIONS_SYSTEM_SUFFIX = (
    "\n\nYOU CAN PRESS X4'S KEYBOARD KEYS for the user via the "
    "propose_x4_action function. When you call this function the keys are "
    "pressed IMMEDIATELY — there is NO confirmation step. Do NOT ask the "
    "user to say 'go' or 'confirm'. Just call the function and announce "
    "what you're doing in present tense ('Opening ship menu', 'Pressing M "
    "for map', 'Deploying satellite').\n"
    "\n"
    "ALWAYS call propose_x4_action when the user asks for any in-game "
    "action:\n"
    "- 'open the map' / 'open ship menu' / 'open inventory'\n"
    "- 'deploy a satellite' / 'launch a probe' / 'fire missiles'\n"
    "- 'dock here' / 'jump to <system>' / 'boost'\n"
    "- 'press 1' / 'press it for me'\n"
    "- 'can you open the X' / 'can you do that' (treat as a request)\n"
    "\n"
    "Source-of-truth rule for which keys to press:\n"
    "1. The X4 KEYBOARD BINDINGS section above is parsed from the user's "
    "ACTUAL inputmap.xml. It is correct for THIS user's setup. Use it.\n"
    "2. The screenshot will often show 'Press 1 to open SHIP MENU' or "
    "similar. THAT '1' IS NOT THE KEYBOARD. It is the user's VKB "
    "controller showing through. PRESSING KEYBOARD '1' WILL NOT WORK. "
    "Always use the bindings table — for ship menu use 'enter', not '1'.\n"
    "3. EXAMPLES:\n"
    "   - User: 'open the ship menu' → keys=['enter']  (NOT keys=['1'])\n"
    "   - User: 'open the map' → keys=['m']\n"
    "   - User: 'boost' → keys=['tab']\n"
    "   - User: 'engage autopilot' → keys=['shift+a']\n"
    "   - User: 'deploy a satellite' → satellite has NO keyboard binding "
    "(joystick only). Decline: 'Deploying satellites isn't bound to the "
    "keyboard, only the joystick — I can't do that one.'\n"
    "4. Never use VKB button names (A4 HAT, etc.) in the function call. "
    "VKB info is only for describing the physical controller in your "
    "spoken reply.\n"
    "5. If you don't see the action in the bindings table and don't know "
    "X4's keyboard default with high confidence, decline politely instead "
    "of guessing.\n"
    "\n"
    "Do NOT call propose_x4_action for:\n"
    "- Pure information questions ('what does this menu do', 'where is X')\n"
    "- Status checks ('what do you see')"
)

PROPOSE_ACTION_TOOL = {
    "type": "function",
    "name": "propose_x4_action",
    "description": (
        "Propose a keyboard action to perform in X4 Foundations. The app "
        "stores this as pending until the user confirms verbally."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action_name": {
                "type": "string",
                "description": "Short human-readable action name, max 6 words.",
            },
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Sequence of key combos to press in order. Use the "
                    "Python keyboard library syntax: single key like 'm', "
                    "combos with '+' like 'shift+1'. Use X4 default keyboard "
                    "bindings."
                ),
            },
            "explanation": {
                "type": "string",
                "description": "One short sentence describing what these keys do in X4.",
            },
        },
        "required": ["action_name", "keys", "explanation"],
        "additionalProperties": False,
    },
    "strict": True,
}


def _extract_text_and_action(response: Any) -> tuple[str, ProposedAction | None]:
    """Pull the text reply and (optional) function-call payload out of a
    Responses API response object. If the model returns only a function call
    without spoken text, synthesize fallback text so the user hears something."""
    text = response.output_text or ""
    action: ProposedAction | None = None
    output = getattr(response, "output", None) or []
    for item in output:
        item_type = getattr(item, "type", None)
        if item_type != "function_call":
            continue
        if getattr(item, "name", None) != "propose_x4_action":
            continue
        raw = getattr(item, "arguments", None)
        if not raw:
            continue
        try:
            args = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue
        keys = args.get("keys") or []
        if not keys:
            continue
        action = ProposedAction(
            name=str(args.get("action_name", "X4 action"))[:80],
            keys=tuple(str(k) for k in keys),
            explanation=str(args.get("explanation", "")),
        )
        break
    if action and not text.strip():
        keys_phrase = " then ".join(action.keys)
        text = f"Pressing {keys_phrase} to {action.name.lower()}."
    return text, action


class OpenAIBrain(Brain):
    """Vision + (optional) web-search + (optional) X4-action-proposal brain
    backed by OpenAI's Responses API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5-nano",
        history_turns: int = 6,
        timeout: float = 60.0,
        vkb_bindings: str | None = None,
        keyboard_defaults: str | None = None,
        web_search: bool = False,
        actions_enabled: bool = True,
        reasoning_effort: str = "minimal",
    ):
        self._model = model
        self._history = ConversationHistory(max_turns=history_turns)
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self._web_search = web_search
        self._actions_enabled = actions_enabled
        self._reasoning_effort = reasoning_effort
        prompt = BASE_SYSTEM_PROMPT
        if vkb_bindings:
            prompt += VKB_PREAMBLE + vkb_bindings
        if actions_enabled and keyboard_defaults:
            prompt += KEYBOARD_DEFAULTS_PREAMBLE + keyboard_defaults
        if actions_enabled:
            prompt += ACTIONS_SYSTEM_SUFFIX
        self._system_prompt = prompt

    async def answer(self, frame: bytes, query: str) -> BrainReply:
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
        tools: list[dict[str, Any]] = []
        if self._web_search:
            tools.append({"type": "web_search_preview"})
        if self._actions_enabled:
            tools.append(PROPOSE_ACTION_TOOL)
        if tools:
            kwargs["tools"] = tools

        response = await self._client.responses.create(**kwargs)
        text, action = _extract_text_and_action(response)
        self._history.append_user(query)
        self._history.append_assistant(text)
        return BrainReply(text=text, pending_action=action)

    async def aclose(self) -> None:
        try:
            await self._client.close()
        except Exception:
            pass
