"""Portuguese OPTION menu (PT-BR fork, docs/TEXTURES.md).

Takes the three OPTION menu textures dumped with RECVX_TEX_DUMP and writes them, 4x larger and
with every English caption rewritten in Portuguese (no accents, as the other game-font menus), to
<mods>/textures/pt/. The rectangles are the ones adv.c DisplayOptionPlateLevel0..3 cuts from the
textures, so each caption stays inside the area the game draws.

    cb5060d84e96c50b  captions (AUDIO SETUP ... EXIT, key names, help text)
    271a7590c63b69f4  controller picture and the big titles (OPTION, KEY CONFIG ...)
    cee1149cc7bbb07f  the photos behind the menu (upscaled only)

    python pc/tools/options_ptbr.py <dump dir> <mods dir> [--esrgan realesrgan-ncnn-vulkan.exe]

With --esrgan (Real-ESRGAN ncnn, github.com/xinntao/Real-ESRGAN) the pictures are upscaled by the
network, otherwise with a Lanczos filter.
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 4
FONT = r"C:\Windows\Fonts\timesbd.ttf"

CAPTIONS = "cb5060d84e96c50b"
TITLES = "271a7590c63b69f4"
PHOTOS = "cee1149cc7bbb07f"

# texture 0 (captions): (u, v, w, h), text, cap height, align
CAPTION_ITEMS = [
    ((0, 0, 288, 32), "AJUSTE DE SOM", 19, "l"),
    ((0, 32, 288, 32), "CONTROLES", 19, "l"),
    ((0, 64, 288, 32), "AJUSTE DE TELA", 19, "l"),
    ((0, 96, 288, 32), "BRILHO DO MONITOR", 19, "l"),
    ((0, 128, 288, 32), "VIBRACAO", 19, "l"),
    ((0, 160, 288, 32), "PADRAO", 19, "l"),
    ((0, 192, 288, 32), "SAIR", 19, "l"),
    ((0, 224, 128, 32), "AJUSTE", 19, "l"),
    ((0, 256, 128, 32), "ESTEREO", 19, "c"),
    ((128, 256, 128, 32), "MONO", 19, "c"),
    ((0, 288, 128, 32), "TIPO", 19, "l"),
    ((0, 320, 128, 32), "SIM", 19, "c"),
    ((128, 320, 128, 32), "NAO", 19, "c"),
    # key names (288, i * 32, 112, 32)
    ((288, 0, 112, 32), "CANCELA/CORRE", 16, "c"),
    ((288, 32, 112, 32), "STATUS", 17, "c"),
    ((288, 64, 112, 32), "OK/ATACA", 17, "c"),
    ((288, 96, 112, 32), "MAPA", 17, "c"),
    ((288, 128, 112, 32), "FRENTE", 17, "c"),
    ((288, 160, 112, 32), "TRAS", 17, "c"),
    ((288, 192, 112, 32), "VIRA ESQ.", 17, "c"),
    ((288, 224, 112, 32), "VIRA DIR.", 17, "c"),
    ((288, 256, 112, 32), "TROCA MIRA", 16, "c"),
    ((288, 288, 112, 32), "MIRAR", 17, "c"),
    ((288, 320, 112, 32), "OPCOES", 17, "c"),
    # the port's ENHANCED SETTINGS row (pc/glue/options_glue.c draws it from here)
    ((400, 256, 224, 32), "AJUSTES DO PORT", 19, "l"),
    ((400, 320, 576, 32), "APERTE QUALQUER BOTAO PARA SAIR", 18, "c"),
]
# help text: (u, v, w, h) of the block, lines (one per 32 px row)
HELP = [
    ((400, 0, 528, 160), 1, ["Para a melhor imagem, ajuste o brilho",
                             "do monitor ate a barra de cor abaixo",
                             "da linha vermelha nao ficar visivel."]),
    ((400, 160, 448, 96), 0, ["Ajuste a posicao da tela com o",
                              "direcional.",
                              "Aperte START para voltar ao padrao."]),
]
# texture 2 (titles): (0, v, 448, 48)
TITLE_ITEMS = [(320, "OPCOES"), (368, "CONTROLES"), (416, "BRILHO DO MONITOR"), (464, "AJUSTE DE TELA")]


def font(cap_px):
    size = cap_px
    while True:
        f = ImageFont.truetype(FONT, size)
        b = f.getbbox("H")
        if b[3] - b[1] >= cap_px:
            return f
        size += 1


def upscale_rgb(img, esrgan):
    """RGB upscale by S: Real-ESRGAN when given, else Lanczos + sharpening."""
    rgb = img.convert("RGB")
    if esrgan:
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = os.path.join(tmp, "in.png"), os.path.join(tmp, "out.png")
            rgb.save(src)
            subprocess.run([esrgan, "-i", src, "-o", dst, "-n", "realesrgan-x4plus", "-s", str(S)],
                           check=True, capture_output=True)
            return Image.open(dst).convert("RGB")
    up = rgb.resize((rgb.width * S, rgb.height * S), Image.LANCZOS)
    return up.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))


def upscale(img, esrgan):
    up = upscale_rgb(img, esrgan).convert("RGBA")
    up.putalpha(img.split()[3].resize(up.size, Image.LANCZOS))
    return up


def ink_color(orig, box):
    """The bright colour of the English caption in box (its lightest 30 %)."""
    u, v, w, h = box
    a = np.array(orig.crop((u, v, u + w, v + h)))
    m = a[:, :, 3] > 64
    if not m.any():
        return (220, 220, 220)
    px = a[m][:, :3]
    lum = px.sum(1)
    top = px[lum >= np.percentile(lum, 70)]
    return tuple(int(c) for c in top.mean(0))


def text_mask(text, f, spacing=0.0):
    """Antialiased mask of text (S-scaled font), tight, with its baseline offset."""
    widths = [f.getlength(c) for c in text]
    w = int(sum(widths) + spacing * (len(text) - 1)) + 8
    asc, desc = f.getmetrics()
    m = Image.new("L", (w, asc + desc + 8), 0)
    d = ImageDraw.Draw(m)
    x = 4
    for c, cw in zip(text, widths):
        d.text((x, 4 + asc), c, font=f, fill=255, anchor="ls")
        x += cw + spacing
    bb = m.getbbox() or (0, 0, 1, 1)
    return m.crop((bb[0], 0, bb[2], m.height)), 4 + asc


def place(out, box, mask, base, baseline_y, align, color, shadow=True):
    """Draws mask into box (1x coords) of the S-scaled out, squeezed to fit the width."""
    u, v, w, h = box
    pad = 3 * S
    maxw = w * S - 2 * pad
    if mask.width > maxw:
        mask = mask.resize((maxw, mask.height), Image.LANCZOS)
    x = u * S + pad if align == "l" else u * S + (w * S - mask.width) // 2
    y = int(baseline_y * S) - base
    full = Image.new("L", out.size, 0)
    full.paste(mask, (x, y))
    if shadow:   # a dark edge as the original captions have
        sh = Image.new("L", out.size, 0)
        sh.paste(mask, (x + S, y + S))
        layer = Image.new("RGBA", out.size, (20, 20, 20, 0))
        layer.putalpha(sh.point(lambda a: a * 128 // 255))
        out.alpha_composite(layer)
    layer = Image.new("RGBA", out.size, color + (0,))
    layer.putalpha(full.point(lambda a: a * 128 // 255))
    out.alpha_composite(layer)


def clear(out, box):
    u, v, w, h = box
    out.paste((0, 0, 0, 0), (u * S, v * S, (u + w) * S, (v + h) * S))


def captions(orig, esrgan):
    out = upscale(orig, esrgan)
    for box, text, cap, align in CAPTION_ITEMS:
        color = ink_color(orig, box) if box[0] < 400 or box[1] == 320 else (220, 220, 220)
        clear(out, box)
        mask, base = text_mask(text, font(cap * S), spacing=1.2 * S)
        place(out, box, mask, base, box[1] + 3 + cap, align, color)
    for box, first, lines in HELP:
        color = ink_color(orig, box)
        clear(out, box)
        f = font(15 * S)
        for i, line in enumerate(lines):
            mask, base = text_mask(line, f, spacing=0.3 * S)
            row = (box[0], box[1] + 32 * (i + first), box[2], 32)
            place(out, row, mask, base, row[1] + 4 + 15, "l", color)
    return out


def titles(orig, esrgan):
    out = upscale(orig, esrgan)
    # the metallic shade of the English titles, row by row (OPTION: 326..363)
    a = np.array(orig)
    prof = []
    for y in range(326, 364):
        row = a[y, 0:448]
        m = row[:, 3] > 64
        prof.append(row[m][:, :3].mean(0) if m.any() else np.array([30, 30, 30]))
    prof = np.array(prof)
    f = font(31 * S)
    for v, text in TITLE_ITEMS:
        box = (0, v, 448, 48)
        clear(out, box)
        mask, base = text_mask(text, f, spacing=1.5 * S)
        maxw = (448 - 8) * S
        if mask.width > maxw:
            mask = mask.resize((maxw, mask.height), Image.LANCZOS)
        x = (448 * S - mask.width) // 2
        y = (v + 6 + 31 + 2) * S - base
        full = Image.new("L", out.size, 0)
        full.paste(mask, (x, y))
        edge = full.filter(ImageFilter.MaxFilter(2 * S + 1))
        layer = Image.new("RGBA", out.size, (28, 26, 25, 0))
        layer.putalpha(edge.point(lambda q: q * 128 // 255))
        out.alpha_composite(layer)
        # fill: the sampled shade stretched over the letters' height
        top, bot = (v + 6) * S, (v + 6 + 33) * S
        shade = np.zeros((out.height, out.width, 3), np.uint8)
        for yy in range(top, bot + 4 * S):
            t = min(len(prof) - 1, max(0, int((yy - top) / (bot - top) * (len(prof) - 4)) + 2))
            shade[yy, :] = np.clip(prof[t] * 1.15, 0, 255)
        layer = Image.fromarray(shade).convert("RGBA")
        layer.putalpha(full.point(lambda q: q * 128 // 255))
        out.alpha_composite(layer)
    return out


def main():
    args = sys.argv[1:]
    esrgan = None
    if "--esrgan" in args:
        i = args.index("--esrgan")
        esrgan = os.path.abspath(args[i + 1])
        del args[i:i + 2]
    dump, mods = args
    dst = os.path.join(mods, "textures", "pt")
    os.makedirs(dst, exist_ok=True)
    load = lambda h: Image.open(os.path.join(dump, h + ".png")).convert("RGBA")
    jobs = [(CAPTIONS, captions), (TITLES, titles), (PHOTOS, upscale)]
    for h, fn in jobs:
        out = fn(load(h), esrgan)
        out.save(os.path.join(dst, h + ".png"))
        print(h, out.size)


if __name__ == "__main__":
    main()
