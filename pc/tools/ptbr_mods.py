"""Builds the Portuguese mods folder from your own disc (PT-BR fork, docs/TRANSLATION.md).

The repository keeps only the Portuguese side (pc/ptbr/): this script applies it to the text and
textures of your disc (PS2 NTSC-U, SLUS-20184) and writes the results to <mods>:

  1. SYSMES.ALD: the messages in pc/ptbr/sistema.txt (text.py import; the others stay as on the disc)
  2. textures/pt: the title and OPCOES menus (title_ptbr.py, options_ptbr.py). Needs the game's
     textures: --exe runs the port once to dump them (title menu, then OPCOES), or --dump points
     at a RECVX_TEX_DUMP folder that already has them.

    python pc/tools/ptbr_mods.py --iso disc.iso --mods <game>/mods --exe build-win/pc/recvx.exe
        [--dump dir] [--esrgan realesrgan-ncnn-vulkan.exe]
"""
import argparse
import os
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
PTBR = os.path.join(os.path.dirname(TOOLS), "ptbr")
TITLE = "64cae74c03148763"
OPTIONS = ["cb5060d84e96c50b", "271a7590c63b69f4", "cee1149cc7bbb07f"]
# title menu, then OPCOES (fourth row: Down x3 from CARREGAR JOGO); RECVX_KEYS holds a key until "-"
KEYS = "%d:Down,%d:-,%d:Down,%d:-,%d:Down,%d:-,%d:Return,%d:-"


def py(script, *args):
    subprocess.run([sys.executable, os.path.join(TOOLS, script), *args], check=True)


def have(dump, hashes):
    return all(os.path.exists(os.path.join(dump, h + ".png")) for h in hashes)


def dump_textures(exe, iso, dump):
    """Runs the port with an empty mods folder (the disc's own textures) until OPCOES has shown."""
    with tempfile.TemporaryDirectory() as tmp:
        save, mods = os.path.join(tmp, "save"), os.path.join(tmp, "mods")
        os.makedirs(save)
        os.makedirs(mods)
        with open(os.path.join(save, "recvx.ini"), "w") as f:
            f.write("skip_intro = 1\nmenu_mouse = 0\n")
        for start in (200, 400, 700):   # the title menu's arrival varies: later each try
            t = [start + i * 10 for i in range(8)]
            env = dict(os.environ, RECVX_TEX_DUMP=dump, RECVX_MODS=mods, RECVX_KEYS=KEYS % tuple(t),
                       RECVX_EXIT_FRAME=str(t[-1] + 300))
            subprocess.run([exe, "--save-dir", save, "--quiet", iso], env=env, cwd=tmp,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
            if have(dump, [TITLE] + OPTIONS):
                return
    sys.exit("the menu textures were not dumped; open OPCOES once with RECVX_TEX_DUMP=%s and use --dump" % dump)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--iso", required=True)
    p.add_argument("--mods", required=True)
    p.add_argument("--exe", help="recvx.exe, to dump the menu textures")
    p.add_argument("--dump", help="texture dump folder (default: a temporary one)")
    p.add_argument("--esrgan", help="realesrgan-ncnn-vulkan for the OPCOES pictures")
    a = p.parse_args()
    iso, mods = os.path.abspath(a.iso), os.path.abspath(a.mods)
    os.makedirs(mods, exist_ok=True)

    py("text.py", "--iso", iso, "import", "--in", PTBR, "--mods", mods)

    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.abspath(a.dump) if a.dump else tmp
        if not have(dump, [TITLE] + OPTIONS):
            if not a.exe:
                print("textures: skipped (pass --exe or --dump)")
                return
            os.makedirs(dump, exist_ok=True)
            dump_textures(os.path.abspath(a.exe), iso, dump)
        py("title_ptbr.py", os.path.join(dump, TITLE + ".png"), mods)
        py("options_ptbr.py", dump, mods, *(["--esrgan", os.path.abspath(a.esrgan)] if a.esrgan else []))
    print("mods em português prontos em", mods)


if __name__ == "__main__":
    main()
