"""Generate the tray/app icon: dark-navy square with white 'X4' centered.

One-shot — run when the icon needs to be regenerated. Output is committed.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SIZE = 64  # render larger, Qt scales down nicely
OUT = Path(__file__).resolve().parent.parent / "src" / "x4_companion" / "data" / "icon.png"

img = Image.new("RGBA", (SIZE, SIZE), (10, 22, 48, 255))
draw = ImageDraw.Draw(img)

# rounded look: trim corners to translucent
mask = Image.new("L", (SIZE, SIZE), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=12, fill=255)
out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
out.paste(img, mask=mask)

# accent bar (cyan, X4 vibe)
ImageDraw.Draw(out).rectangle((6, SIZE - 10, SIZE - 6, SIZE - 6), fill=(0, 200, 230, 255))

# 'X4' centered
try:
    font = ImageFont.truetype("arial.ttf", 32)
except OSError:
    font = ImageFont.load_default()
text = "X4"
bbox = ImageDraw.Draw(out).textbbox((0, 0), text, font=font)
tx = (SIZE - (bbox[2] - bbox[0])) / 2 - bbox[0]
ty = (SIZE - (bbox[3] - bbox[1])) / 2 - bbox[1] - 4
ImageDraw.Draw(out).text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

OUT.parent.mkdir(parents=True, exist_ok=True)
out.save(OUT, format="PNG")
print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")

# Also write a multi-resolution .ico for Windows shortcuts
ICO_OUT = OUT.with_suffix(".ico")
out.save(ICO_OUT, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
print(f"wrote {ICO_OUT} ({ICO_OUT.stat().st_size} bytes)")
