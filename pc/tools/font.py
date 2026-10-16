#!/usr/bin/env python3
"""Add accented letters to the game's message font (docs/TRANSLATION.md).

  font.py [--iso ISO] [--mods mods] [--preview scratch/font_page0.png]

The font is the first texture of SYSEFF.ALD (SYSTEM.AFS entry 1, loaded by effect.c
bhInitEffect into sys->ef_tlist): a 512x512 4-bit TIM2 with 18x18 cells of 28x28 pixels
(message.c bhDispFont, code % 324). Codes 108.. are empty on the disc. For every entry of
text.py EXTRA_GLYPHS this script copies the base letter into the code's cell and draws the
diacritic in the font's own style (palette 7 = outline, 1..6 = fill shades), then writes the
whole entry to <mods>/SYSTEM.AFS/1. Output is derived from your disc: keep it in mods/.
"""
import argparse, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdx  # noqa: E402
import text  # noqa: E402

CELL = 28
PER_ROW = 18
OUTLINE = 7
FILL = 2

# Diacritic masks: (x, y) pixels of the mark's core, before the outline is added.
MARKS = {
    'acute': [(0, 4), (1, 4), (1, 3), (2, 3), (2, 2), (3, 2), (3, 1), (4, 1), (4, 0), (5, 0)],
    'grave': [(5, 4), (4, 4), (4, 3), (3, 3), (3, 2), (2, 2), (2, 1), (1, 1), (1, 0), (0, 0)],
    'circumflex': [(0, 4), (1, 3), (1, 4), (2, 2), (2, 3), (3, 1), (3, 2), (4, 2), (4, 3), (5, 3), (5, 4), (6, 4),
                   (3, 0)],
    'tilde': [(0, 3), (0, 2), (1, 1), (2, 1), (2, 0), (3, 1), (4, 2), (5, 2), (5, 3), (6, 2), (7, 1), (7, 0)],
    'diaeresis': [(0, 1), (1, 1), (0, 2), (1, 2), (5, 1), (6, 1), (5, 2), (6, 2)],
    'cedilla': [(2, 0), (2, 1), (3, 2), (4, 3), (3, 4), (2, 4), (1, 4)],
}


class Page:
    def __init__(self, data, tim_ofs):
        self.d = data
        hdr = tim_ofs + 0xA0
        tot, csz, isz, hsz, ccol, fmt, mip, ctype, itype, w, h = struct.unpack_from('<IIIHHBBBBHH', data, hdr)
        if itype != 4 or (w, h) != (512, 512):
            sys.exit('unexpected font texture (%dx%d, type %d)' % (w, h, itype))
        self.img, self.w, self.h = hdr + hsz, w, h
        self.clut = [data[self.img + isz + 4 * i:self.img + isz + 4 * i + 4] for i in range(16)]

    def get(self, x, y):
        b = self.d[self.img + (y * self.w + x) // 2]
        return b & 15 if x % 2 == 0 else b >> 4

    def put(self, x, y, v):
        i = self.img + (y * self.w + x) // 2
        b = self.d[i]
        self.d[i] = (b & 0xF0) | v if x % 2 == 0 else (b & 0x0F) | (v << 4)

    def cell(self, code):
        cx, cy = (code % PER_ROW) * CELL, (code // PER_ROW) * CELL
        return [[self.get(cx + x, cy + y) for x in range(CELL)] for y in range(CELL)]

    def set_cell(self, code, px):
        cx, cy = (code % PER_ROW) * CELL, (code // PER_ROW) * CELL
        for y in range(CELL):
            for x in range(CELL):
                self.put(cx + x, cy + y, px[y][x])

    def rgba(self):
        out = bytearray()
        for y in range(self.h):
            for x in range(self.w):
                c = self.clut[self.get(x, y)]
                out += bytes((c[0], c[1], c[2], min(255, c[3] * 2)))
        return bytes(out)


def bbox(px):
    xs = [x for y in range(CELL) for x in range(CELL) if px[y][x]]
    ys = [y for y in range(CELL) if any(px[y])]
    return min(xs), max(xs), min(ys), max(ys)


def squash(px, top, new_top, bottom):
    """Resample rows top..bottom into new_top..bottom (nearest), clearing the rows above."""
    out = [[0] * CELL for _ in range(CELL)]
    for y in range(CELL):
        if y > bottom:
            out[y] = list(px[y])
    span_src, span_dst = bottom - top, bottom - new_top
    for y in range(new_top, bottom + 1):
        src = top + round((y - new_top) * span_src / span_dst) if span_dst else top
        out[y] = list(px[src])
    return out


def draw_mark(px, mark, ox, oy):
    pts = {(ox + x, oy + y) for x, y in MARKS[mark] if 0 <= ox + x < CELL and 0 <= oy + y < CELL}
    for x, y in pts:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < CELL and 0 <= ny < CELL and (nx, ny) not in pts and px[ny][nx] == 0:
                    px[ny][nx] = OUTLINE
    for x, y in pts:
        px[y][x] = FILL


def make_glyph(page, base, mark):
    px = page.cell(ord(base) - 32)
    x0, x1, y0, y1 = bbox(px)
    w = max(x for x, _ in MARKS[mark]) + 1
    h = max(y for _, y in MARKS[mark]) + 1
    cx = (x0 + x1 + 1) // 2 - w // 2
    if mark == 'cedilla':
        draw_mark(px, mark, cx, y1 + 1)
        return px
    if base.isupper() or base in 'bdfhklt':
        # capitals reach the top of the cell: make room for the mark
        px = squash(px, y0, y0 + h + 2, y1)
        y0 = y0 + h + 2
    if base == 'i':
        # replace the dot of the i by the mark
        for y in range(y0, y0 + 6):
            px[y] = [0] * CELL
        px_rows = [y for y in range(CELL) if any(px[y])]
        y0 = px_rows[0]
    draw_mark(px, mark, cx, max(0, y0 - h - 1))
    return px


def font_entry(iso):
    return bytearray(rdx.Afs(iso, 'SYSTEM.AFS').get(1))


def find_font(d):
    o = d.find(b'TIM2')
    while o >= 0 and d[o + 32:o + 36] != b'TIM2':
        o = d.find(b'TIM2', o + 4)
    if o < 0:
        sys.exit('font texture not found in SYSEFF')
    return o


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--iso')
    p.add_argument('--mods', default='mods')
    p.add_argument('--preview', help='also write the edited font page as PNG')
    args = p.parse_args()
    iso_path = args.iso or os.environ.get('RECVX_ISO')
    if not iso_path or not os.path.exists(iso_path):
        sys.exit('disc image not found: pass --iso or set RECVX_ISO')
    iso = rdx.Iso(iso_path)
    d = font_entry(iso)
    page = Page(d, find_font(d))
    for ch, code, base, mark in text.EXTRA_GLYPHS:
        if any(any(r) for r in page.cell(code)):
            sys.exit('cell %d is not empty on this disc' % code)
        page.set_cell(code, make_glyph(page, base, mark))
    out_dir = os.path.join(args.mods, 'SYSTEM.AFS')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, '1'), 'wb') as f:
        f.write(page.d)
    if args.preview:
        os.makedirs(os.path.dirname(args.preview) or '.', exist_ok=True)
        rdx.write_png(args.preview, page.w, page.h, page.rgba())
    print('%d glifos em %s' % (len(text.EXTRA_GLYPHS), os.path.join(out_dir, '1')))


if __name__ == '__main__':
    main()
