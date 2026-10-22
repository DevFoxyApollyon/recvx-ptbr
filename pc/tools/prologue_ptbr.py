"""Portuguese opening text (PT-BR fork, docs/TEXTURES.md).

The text that scrolls before a new game ("The American mid-western town...") is two 512x512
textures with one line every 32 px from y 153, x 104. This draws them in Portuguese, 4x larger,
from nothing (no picture of the disc is needed: they are only text on transparency), into
<mods>/textures/pt/.

    python pc/tools/prologue_ptbr.py <mods>
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

S = 4
FONTS = [r"C:\Windows\Fonts\pala.ttf", r"C:\Windows\Fonts\georgia.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]
COLOR = (182, 196, 196)
PAGES = {
    "7c49072c74e82d93": [
        "A cidade de Raccoon City,",
        "no meio-oeste americano,",
        "foi totalmente destruida",
        "pelo surto do Virus-T,",
        "provocado pela empresa",
        "internacional",
        '"Umbrella".',
    ],
    "72147cd75fcc3613": [
        "Claire Redfield,",
        "que chegou a Raccoon City",
        "procurando o irmao Chris,",
        "e o policial novato",
        "Leon S. Kennedy",
        "conseguiram fugir da cidade,",
        "mas o pesadelo deles era so",
        "o comeco do que estava por vir...",
    ],
}
X, Y0, PITCH, CAP, MAXW = 104, 153, 32, 16, 400


def font():
    path = next(p for p in FONTS if os.path.exists(p))
    size = CAP * S
    while True:
        f = ImageFont.truetype(path, size)
        b = f.getbbox("H")
        if b[3] - b[1] >= CAP * S:
            return f
        size += 1


def page(lines, f):
    im = Image.new("RGBA", (512 * S, 512 * S), COLOR + (0,))
    mask = Image.new("L", im.size, 0)
    for i, text in enumerate(lines):
        line = Image.new("L", (int(f.getlength(text)) + 8 * S, PITCH * S), 0)
        ImageDraw.Draw(line).text((0, (CAP + 1) * S), text, font=f, fill=255, anchor="ls")
        if line.width > MAXW * S:
            line = line.resize((MAXW * S, line.height), Image.LANCZOS)
        mask.paste(line, (X * S, (Y0 + PITCH * i) * S))
    im.putalpha(mask.point(lambda a: a * 128 // 255))   # PS2 alpha: 128 = opaque
    return im


def main(mods):
    dst = os.path.join(mods, "textures", "pt")
    os.makedirs(dst, exist_ok=True)
    f = font()
    for h, lines in PAGES.items():
        page(lines, f).save(os.path.join(dst, h + ".png"))
        print(h)


if __name__ == "__main__":
    main(sys.argv[1])
