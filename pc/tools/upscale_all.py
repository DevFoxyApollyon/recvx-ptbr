"""Upscales every dumped game texture with Real-ESRGAN into mods/textures (PT-BR fork,
docs/TEXTURES.md).

Play with RECVX_TEX_DUMP=<dump> (each texture the game loads is saved once as <hash>.png), then:

    python pc/tools/upscale_all.py <dump> <mods> --esrgan realesrgan-ncnn-vulkan.exe [--scale 4]

Every PNG of the dump that has no file in <mods>/textures yet goes through the network
(realesrgan-x4plus) and is written as <mods>/textures/<hash>.png with the original alpha (0..128,
128 = opaque) upscaled smoothly. Textures already there (your own or a translated one in
textures/pt) are kept, so it can run again after each play session. Textures smaller than
16x16 are skipped (a 4x of a flat colour gains nothing).
"""
import argparse
import glob
import os
import subprocess
import sys
import tempfile

from PIL import Image

MIN = 16


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("mods")
    ap.add_argument("--esrgan", required=True)
    ap.add_argument("--scale", type=int, default=4)
    args = ap.parse_args()
    esrgan = os.path.abspath(args.esrgan)
    dst = os.path.join(args.mods, "textures")
    os.makedirs(dst, exist_ok=True)
    have = {os.path.basename(p) for p in glob.glob(os.path.join(dst, "*.png"))}
    have |= {os.path.basename(p) for p in glob.glob(os.path.join(dst, "pt", "*.png"))}
    todo = []
    for p in sorted(glob.glob(os.path.join(args.dump, "*.png"))):
        name = os.path.basename(p)
        if name in have:
            continue
        im = Image.open(p)
        if min(im.size) < MIN:
            continue
        todo.append(p)
    print(len(todo), "textures to upscale")
    with tempfile.TemporaryDirectory() as tmp:
        src_dir, out_dir = os.path.join(tmp, "in"), os.path.join(tmp, "out")
        os.makedirs(src_dir)
        os.makedirs(out_dir)
        for p in todo:
            Image.open(p).convert("RGB").save(os.path.join(src_dir, os.path.basename(p)))
        if todo:   # one run over the folder: the network loads once
            subprocess.run([esrgan, "-i", src_dir, "-o", out_dir, "-n", "realesrgan-x4plus",
                            "-s", str(args.scale), "-f", "png"], check=True, capture_output=True)
        done = 0
        for p in todo:
            name = os.path.basename(p)
            up = os.path.join(out_dir, name)
            if not os.path.exists(up):
                print("failed:", name, file=sys.stderr)
                continue
            rgb = Image.open(up).convert("RGBA")
            alpha = Image.open(p).convert("RGBA").split()[3].resize(rgb.size, Image.LANCZOS)
            rgb.putalpha(alpha)
            rgb.save(os.path.join(dst, name))
            done += 1
    print(done, "written to", dst)


if __name__ == "__main__":
    main()
