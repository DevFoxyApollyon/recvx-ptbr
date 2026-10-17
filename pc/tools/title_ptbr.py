"""Portuguese title menu plates (PT-BR fork, docs/TEXTURES.md).

Takes the title plates texture dumped with RECVX_TEX_DUMP (64cae74c03148763.png, 512x512, the
English "LOAD GAME" ... pictures) and writes mods/textures/pt/64cae74c03148763.png: the same
texture at 4x with the menu rows rewritten in Portuguese (no accents, as the other game-font
menus) in a bold serif close to the original, and the rows it does not translate upscaled.
Row 192 (SOUND MUSEUM, not used by this version) becomes MULTIJOGADOR, which the port draws from
there when this file is in use.

    python pc/tools/title_ptbr.py <dump dir>/64cae74c03148763.png <mods dir>
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 4                      # upscale
ROWS = {                   # v of the row (32 px each) -> text
    32: "PRESSIONE START",
    64: "CARREGAR JOGO",
    96: "NOVO JOGO",
    128: "OPCOES",
    160: "SELECAO DE MODO",
    192: "MULTIJOGADOR",
    224: "MODO BATALHA",
}
FONTS = [r"C:\Windows\Fonts\timesbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]


def font(cap_px):
    path = next(p for p in FONTS if os.path.exists(p))
    size = cap_px
    while True:   # point size whose capital H is cap_px tall
        f = ImageFont.truetype(path, size)
        b = f.getbbox("H")
        if b[3] - b[1] >= cap_px:
            return f
        size += 1


def main(src, mods):
    orig = Image.open(src).convert("RGBA")
    w, h = orig.size
    # the rows kept: upscaled (alpha too: 0..128 as the PS2 texture, 128 = opaque)
    out = orig.resize((w * S, h * S), Image.LANCZOS)
    out = out.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    f = font(20 * S)
    for v, text in ROWS.items():
        top = v * S
        out.paste((0, 0, 0, 0), (0, top, w * S, top + 32 * S))
        tw = f.getlength(text) + 2 * S * 1.6   # letter spacing as the plates
        tw = sum(f.getlength(c) for c in text) + (len(text) - 1) * S * 1.6
        x0 = (w * S - tw) / 2
        base = top + 26 * S
        mask_hi = Image.new("L", out.size, 0)
        mask_sh = Image.new("L", out.size, 0)
        dh, ds = ImageDraw.Draw(mask_hi), ImageDraw.Draw(mask_sh)
        x = x0
        for c in text:
            dh.text((x, base), c, font=f, fill=255, anchor="ls")
            ds.text((x + 1.2 * S, base + 1.2 * S), c, font=f, fill=255, anchor="ls")
            x += f.getlength(c) + S * 1.6
        # grey bevel (bottom right), then the white face with a slight top-to-bottom shade
        grey = Image.new("RGBA", out.size, (96, 96, 96, 0))
        grey.putalpha(mask_sh.point(lambda a: a * 128 // 255))
        out.alpha_composite(grey)
        face = Image.new("RGBA", out.size, (0, 0, 0, 0))
        fd = ImageDraw.Draw(face)
        for yy in range(top, top + 32 * S):
            t = (yy - top - 6 * S) / (20 * S)
            g = int(255 - 26 * max(0.0, min(1.0, t)))
            fd.line([(0, yy), (w * S, yy)], fill=(g, g, g, 0))
        face.putalpha(mask_hi.point(lambda a: a * 128 // 255))
        out.alpha_composite(face)
    dst = os.path.join(mods, "textures", "pt")
    os.makedirs(dst, exist_ok=True)
    name = os.path.join(dst, os.path.basename(src))
    out.save(name)
    print(name, out.size)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
