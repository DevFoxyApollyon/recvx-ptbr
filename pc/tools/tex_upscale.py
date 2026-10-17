"""Upscales dumped textures into mods/textures (PT-BR fork, docs/TEXTURES.md).

    python pc/tools/tex_upscale.py <mods dir> <dump dir>/<hash>.png [...] [--scale 3]

A classic filter (Lanczos plus sharpening, no new detail): a starting point. For a real gain,
run the PNG through an AI upscaler (Real-ESRGAN, waifu2x, ...) and save the result with the same
name in <mods>/textures - any size works, the game samples it in normalized coordinates. Keep
the alpha channel as it is in the dump (0..128, 128 = opaque).
"""
import os
import sys
from PIL import Image, ImageFilter


def upscale(src, mods, scale):
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    rgb = im.convert("RGB").resize((w * scale, h * scale), Image.LANCZOS)
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.6 * scale / 2, percent=70, threshold=3))
    alpha = im.split()[3].resize(rgb.size, Image.LANCZOS)
    rgb.putalpha(alpha)
    dst = os.path.join(mods, "textures")
    os.makedirs(dst, exist_ok=True)
    out = os.path.join(dst, os.path.basename(src))
    rgb.save(out)
    print(out, rgb.size)


if __name__ == "__main__":
    args = sys.argv[1:]
    scale = 3
    if "--scale" in args:
        i = args.index("--scale")
        scale = int(args[i + 1])
        del args[i:i + 2]
    for p in args[1:]:
        upscale(p, args[0], scale)
