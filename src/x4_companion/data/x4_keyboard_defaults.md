# X4: Foundations — default KEYBOARD bindings

This file is the source of truth for the **X4 Companion's** keyboard
execution. The companion sends OS-level keyboard events, so action proposals
must use **keyboard keys** here, never VKB stick button names.

If the screenshot shows a contextual hint like `Press <key> to <action>`,
**use that key literally** — it wins over this list. The user may have
remapped some bindings.

## Menus

- `1` — Open Ship Menu / Pilot Menu
- `2` — Open Player Information menu
- `3` — Open Map (small / sector)
- `4` — Open Personal/Property menu
- `5` — Open Encyclopedia
- `M` — Open Big Map (full-screen, system)
- `Esc` — Open Game Menu (or close current menu)
- `Backspace` — Back / close active menu
- `Enter` — Confirm / activate
- `` ` `` — Quick pause

## Flight / piloting

- `Tab` — Toggle Travel Mode (boost cruise)
- `Shift+Space` — Steering mode (mouse flight)
- `B` — Boost (short burst)
- `Z` — Brake
- `X` — Roll mode toggle
- `Q` — Toggle aim assist
- `U` — Toggle Autopilot
- `Shift+D` — Dock at target / fly through target gate
- `T` — Target locked object
- `E` — Interact / use / dock prompt

## Scanning

- `F` — Long Range Scanner toggle
- `Shift+F` — LRS scan mode toggle

## Combat

- Left mouse — Fire main guns
- Right mouse — Fire missiles
- `Ctrl+1` / `Ctrl+2` / … — Fire weapon group N
- `Shift+Q` — Cycle weapon mode

## Camera

- `F1` — Cockpit view
- `F2` — External chase camera
- `F3` — Free / cinematic camera

## Comms / HUD

- `C` — Comms with selected target
- `Shift+H` — Toggle HUD

## Deployables (multi-step)

Deployables (satellites, resource probes, laser towers, nav beacons, mines)
are normally chosen via a deploy menu — they are **not single-key actions**.
A typical sequence is "open the deploy submenu, navigate, confirm." If the
user asks to deploy something, prefer using the screenshot's on-screen hints
over guessing a sequence. If unsure, decline politely instead of pressing
random keys.

## Notes

- All listed keys assume X4's stock defaults. If a user has remapped, the
  screenshot hint takes precedence.
- For multi-step actions the model may propose a sequence of keys; the
  companion presses them in order with a short delay between each.
