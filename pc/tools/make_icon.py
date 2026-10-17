"""Draws the program icon pc/res/recvx.ico (PT-BR fork): a crimson serif X over a dark plate,
with CODE: VERONICA under it at the larger sizes. Original drawing (no game picture).

    python pc/tools/make_icon.py
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SERIF = r"C:\Windows\Fonts\timesbd.ttf"
OUT = os.path.join(os.path.dirname(__file__), "..", "res", "recvx.ico")


def draw(n):
    s = 4 * n   # supersampled
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = s // 7
    # dark plate with a thin red rim
    d.rounded_rectangle((0, 0, s - 1, s - 1), r, fill=(16, 10, 12, 255))
    d.rounded_rectangle((s * 0.03, s * 0.03, s * 0.97, s * 0.97), r * 0.85, outline=(120, 14, 20, 255),
                        width=max(1, s // 64))
    big = n >= 48
    f = ImageFont.truetype(SERIF, int(s * (0.92 if big else 1.05)))
    cy = s * (0.45 if big else 0.53)
    # glow, silver edge, crimson letter
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((s / 2, cy), "X", font=f, anchor="mm", fill=(200, 20, 30, 200))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s / 30)))
    d.text((s / 2, cy), "X", font=f, anchor="mm", fill=(150, 10, 18, 255),
           stroke_width=max(2, s // 90), stroke_fill=(215, 210, 205, 255))
    if big:
        size = int(s * 0.13)
        while ImageFont.truetype(SERIF, size).getlength("CODE:VERONICA") > s * 0.8:
            size -= 1
        g = ImageFont.truetype(SERIF, size)
        d.text((s / 2, s * 0.86), "CODE:VERONICA", font=g, anchor="mm", fill=(225, 220, 215, 255))
    return im.resize((n, n), Image.LANCZOS)


if __name__ == "__main__":
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [draw(n) for n in sizes]
    imgs[-1].save(OUT, sizes=[(n, n) for n in sizes], append_images=imgs[:-1])
    imgs[-1].save(OUT.replace(".ico", ".png"))
    print(os.path.abspath(OUT))
