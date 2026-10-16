#!/usr/bin/env python3
"""Game text: export the messages of every room and of SYSMES.ALD to editable UTF-8 files, and
build mods from the edited files (docs/TRANSLATION.md).

  text.py export [--iso ISO] [--out translation]
  text.py import [--iso ISO] [--in translation] [--mods mods]
  text.py check  [--iso ISO]                      # export + import round trip must be lossless

Messages are u16 glyph codes (message.c bhDispMessage): code c < 95 is ASCII c + 32, 0xFFxx are
control codes, 0xFFFF ends a message. Accented letters use the extra glyphs that font.py adds to
the font (EXTRA_GLYPHS below); the port's message.c knows their widths.

The exported files contain the game's own text: they stay in the ignored translation/ folder and
the built mods in the ignored mods/ folder. Never commit or share them.
"""
import argparse, os, re, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdx  # noqa: E402

# ---------------------------------------------------------------- character table
# Extra glyphs drawn by font.py into the free cells of font page 0 (codes 108..). Keep this list in
# sync with decomp message.c FontSz (the widths come from the base letters).
EXTRA_GLYPHS = [
    # char, code, base letter, diacritic
    ('á', 108, 'a', 'acute'), ('à', 109, 'a', 'grave'), ('â', 110, 'a', 'circumflex'), ('ã', 111, 'a', 'tilde'),
    ('é', 112, 'e', 'acute'), ('ê', 113, 'e', 'circumflex'), ('í', 114, 'i', 'acute'), ('ó', 115, 'o', 'acute'),
    ('ô', 116, 'o', 'circumflex'), ('õ', 117, 'o', 'tilde'), ('ú', 118, 'u', 'acute'), ('ü', 119, 'u', 'diaeresis'),
    ('ç', 120, 'c', 'cedilla'),
    ('Á', 121, 'A', 'acute'), ('À', 122, 'A', 'grave'), ('Â', 123, 'A', 'circumflex'), ('Ã', 124, 'A', 'tilde'),
    ('É', 125, 'E', 'acute'), ('Ê', 126, 'E', 'circumflex'), ('Í', 127, 'I', 'acute'), ('Ó', 128, 'O', 'acute'),
    ('Ô', 129, 'O', 'circumflex'), ('Õ', 130, 'O', 'tilde'), ('Ú', 131, 'U', 'acute'), ('Ç', 132, 'C', 'cedilla'),
    ('ñ', 133, 'n', 'tilde'), ('Ñ', 134, 'N', 'tilde'),
]
CHAR_TO_CODE = {c: code for c, code, _, _ in EXTRA_GLYPHS}
CODE_TO_CHAR = {code: c for c, code, _, _ in EXTRA_GLYPHS}

# Control codes with a readable tag. 0xFF01 (half-width space) is the ordinary space between words.
TAGS = {0xFF00: None, 0xFF04: '{espaco}'}
ARG_CODES = (0xFF02, 0xFF03)  # followed by one parameter word
ENTRY_RE = re.compile(r'^### (\d+)\s*$')
TAG_RE = re.compile(r'\{([^{}]*)\}')


def decode(words):
    """u16 codes (without the terminator) -> editable text. Newlines are real line breaks."""
    out, i = [], 0
    while i < len(words):
        c = words[i]
        i += 1
        if c == 0xFF00:
            out.append('\n')
        elif c == 0xFF01:
            out.append(' ')
        elif c in TAGS:
            out.append(TAGS[c])
        elif c in ARG_CODES and i < len(words):
            out.append('{%04X:%04X}' % (c, words[i]))
            i += 1
        elif c == 0:
            out.append('{_}')  # full-width space glyph (code 0), distinct from the word space
        elif c < 95 and chr(c + 32) not in '{}':
            out.append(chr(c + 32))
        elif c in CODE_TO_CHAR:
            out.append(CODE_TO_CHAR[c])
        else:
            out.append('{%04X}' % c)
    return ''.join(out)


def encode(text, where=''):
    """editable text -> u16 codes (without the terminator)."""
    words, pos = [], 0
    while pos < len(text):
        ch = text[pos]
        if ch == '{':
            m = TAG_RE.match(text, pos)
            if not m:
                sys.exit('%s: unclosed "{" in %r' % (where, text[pos:pos + 20]))
            tag = m.group(1)
            pos = m.end()
            if tag == '_':
                words.append(0)
            elif tag == 'espaco':
                words.append(0xFF04)
            elif re.fullmatch(r'[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}', tag):
                a, b = tag.split(':')
                words += [int(a, 16), int(b, 16)]
            elif re.fullmatch(r'[0-9A-Fa-f]{4}', tag):
                words.append(int(tag, 16))
            else:
                sys.exit('%s: unknown tag {%s}' % (where, tag))
            continue
        pos += 1
        if ch == '\n':
            words.append(0xFF00)
        elif ch == ' ':
            words.append(0xFF01)
        elif ch in CHAR_TO_CODE:
            words.append(CHAR_TO_CODE[ch])
        elif 32 < ord(ch) < 127:
            words.append(ord(ch) - 32)
        else:
            sys.exit('%s: the font has no glyph for %r (add it to EXTRA_GLYPHS and font.py)' % (where, ch))
    return words


# ---------------------------------------------------------------- message tables
def read_table(d, base, count):
    """Table at base: u32 entry 0, then one u32 offset (from base) per message."""
    msgs = []
    for i in range(count):
        o = base + rdx.u32(d, base + 4 * (i + 1))
        words = []
        while True:
            c = struct.unpack_from('<H', d, o + 2 * len(words))[0]
            if c == 0xFFFF:
                break
            words.append(c)
        msgs.append(words)
    return msgs


def build_table(head0, msgs):
    """u32 entry 0 kept as found, one offset per message, then the u16 strings (4-byte aligned)."""
    n = len(msgs)
    out = bytearray(struct.pack('<I', head0) + bytes(4 * n))
    for i, words in enumerate(msgs):
        struct.pack_into('<I', out, 4 * (i + 1), len(out))
        out += struct.pack('<%dH' % (len(words) + 1), *words, 0xFFFF)
        while len(out) % 4:
            out += b'\xff'
    return bytes(out)


def sysmes_tables(d):
    """SYSMES.ALD: u32 size, item-name table, u32 size, system-message table (system.c case 1-2)."""
    n_items = rdx.u32(d, 0)
    items = 4
    sysm = 4 + n_items + 4
    return items, sysm


def table_count(d, base, limit):
    """Message tables carry no count: the first offset marks where the strings start."""
    first = rdx.u32(d, base + 4)
    return min((first // 4) - 1, limit)


# ---------------------------------------------------------------- files
def write_entries(path, title, msgs):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# %s: %d mensagens. Edite o texto abaixo de cada "### N"; quebras de linha valem.\n' % (title, len(msgs)))
        f.write('# Tags: {espaco} espaco largo, {_} espaco do glifo 0, {XXXX} codigo do jogo (nao apague).\n\n')
        for i, words in enumerate(msgs):
            f.write('### %d\n%s\n\n' % (i, decode(words)))


def read_entries(path):
    entries, cur, lines = {}, None, []
    with open(path, encoding='utf-8') as f:
        content = f.read().replace('\r\n', '\n')
        if content.endswith('\n'):
            content = content[:-1]  # the file's own final newline is not part of the last message
        for line in content.split('\n'):
            m = ENTRY_RE.match(line)
            if m:
                if cur is not None:
                    entries[cur] = lines
                cur, lines = int(m.group(1)), []
            elif cur is not None:
                lines.append(line)
            # lines before the first entry are comments
    if cur is not None:
        entries[cur] = lines
    # each entry ends with one blank separator line
    return {k: '\n'.join(v[:-1] if v and v[-1] == '' else v) for k, v in entries.items()}


def disc(args):
    iso = args.iso or os.environ.get('RECVX_ISO')
    if not iso or not os.path.exists(iso):
        sys.exit('disc image not found: pass --iso or set RECVX_ISO')
    return rdx.Iso(iso)


def room_tables(iso):
    afs = rdx.Afs(iso, 'RDX_LNK.AFS')
    for i, name in enumerate(rdx.room_names()):
        raw = afs.get(i)
        d = rdx.expand(raw)
        room = rdx.Room(d, name)
        if room.ptr['mesp'] and room.cnt['mes']:
            yield name, d, room


def sysmes_file(iso):
    lsn, size = iso.find('SYSMES.ALD')
    return iso.read(lsn, (size + rdx.SECTOR - 1) // rdx.SECTOR)[:size]


def cmd_export(args):
    iso = disc(args)
    os.makedirs(os.path.join(args.out, 'salas'), exist_ok=True)
    n = 0
    for name, d, room in room_tables(iso):
        msgs = read_table(d, room.ptr['mesp'], room.cnt['mes'])
        write_entries(os.path.join(args.out, 'salas', name[:-4] + '.txt'), name, msgs)
        n += 1
    d = sysmes_file(iso)
    items, sysm = sysmes_tables(d)
    write_entries(os.path.join(args.out, 'itens.txt'), 'SYSMES.ALD (nomes de itens)',
                  read_table(d, items, table_count(d, items, 4096)))
    write_entries(os.path.join(args.out, 'sistema.txt'), 'SYSMES.ALD (mensagens do sistema)',
                  read_table(d, sysm, table_count(d, sysm, 4096)))
    print('%d salas + itens.txt + sistema.txt em %s' % (n, args.out))


def edited(path, msgs):
    """Return the edited messages for a file, or None when nothing changed."""
    if not os.path.exists(path):
        return None
    entries = read_entries(path)
    new = []
    for i, words in enumerate(msgs):
        text = entries.get(i)
        new.append(words if text is None else encode(text, '%s ### %d' % (os.path.basename(path), i)))
    return None if new == msgs else new


def rebuild_room(d, room, new_msgs):
    """Append the new message table at the end of the expanded room and repoint mesp. Rooms only
    use their section offsets (docs/modding/ROOM_FORMAT.md), so the old table can stay in place."""
    base = room.ptr['mesp']
    head0 = rdx.u32(d, base)
    out = bytearray(d)
    while len(out) % 16:
        out.append(0)
    newp = len(out)
    out += build_table(head0, new_msgs)
    struct.pack_into('<I', out, room.rom_ofs + 4 * rdx.ROM_PTRS.index('mesp'), newp)
    return bytes(out)


def rebuild_sysmes(d, new_items, new_sys):
    items, sysm = sysmes_tables(d)
    if new_items is None:
        new_items = read_table(d, items, table_count(d, items, 4096))
    if new_sys is None:
        new_sys = read_table(d, sysm, table_count(d, sysm, 4096))
    ti = build_table(rdx.u32(d, items), new_items)
    ts = build_table(rdx.u32(d, sysm), new_sys)
    # The game skips the second size word (system.c: mes_sp = datp + 4); keep it meaningful anyway.
    return struct.pack('<I', len(ti)) + ti + struct.pack('<I', len(ts)) + ts


def cmd_import(args):
    iso = disc(args)
    os.makedirs(args.mods, exist_ok=True)
    changed = 0
    for name, d, room in room_tables(iso):
        msgs = read_table(d, room.ptr['mesp'], room.cnt['mes'])
        new = edited(os.path.join(args.inp, 'salas', name[:-4] + '.txt'), msgs)
        dst = os.path.join(args.mods, name)
        if new is None:
            continue
        with open(dst, 'wb') as f:
            f.write(rdx.compress(rebuild_room(d, room, new)))
        changed += 1
    d = sysmes_file(iso)
    items, sysm = sysmes_tables(d)
    new_items = edited(os.path.join(args.inp, 'itens.txt'), read_table(d, items, table_count(d, items, 4096)))
    new_sys = edited(os.path.join(args.inp, 'sistema.txt'), read_table(d, sysm, table_count(d, sysm, 4096)))
    if new_items is not None or new_sys is not None:
        with open(os.path.join(args.mods, 'SYSMES.ALD'), 'wb') as f:
            f.write(rebuild_sysmes(d, new_items, new_sys))
        changed += 1
    print('%d arquivo(s) gerado(s) em %s' % (changed, args.mods))


def cmd_check(args):
    """Every message must survive decode -> encode, and a rebuilt table must read back the same."""
    import tempfile
    iso = disc(args)
    total = 0
    tmp = os.path.join(tempfile.mkdtemp(), 'check.txt')
    for name, d, room in room_tables(iso):
        msgs = read_table(d, room.ptr['mesp'], room.cnt['mes'])
        for i, w in enumerate(msgs):
            if encode(decode(w), name) != w:
                sys.exit('%s ### %d: decode/encode is not lossless' % (name, i))
        write_entries(tmp, name, msgs)  # an untouched exported file must not count as edited
        if edited(tmp, msgs) is not None:
            sys.exit('%s: exported file does not read back unchanged' % name)
        rebuilt = rdx.Room(rebuild_room(d, room, msgs), name)
        if read_table(rebuilt.d, rebuilt.ptr['mesp'], rebuilt.cnt['mes']) != msgs:
            sys.exit('%s: rebuilt table differs' % name)
        total += len(msgs)
    d = sysmes_file(iso)
    items, sysm = sysmes_tables(d)
    a = read_table(d, items, table_count(d, items, 4096))
    b = read_table(d, sysm, table_count(d, sysm, 4096))
    for w in a + b:
        if encode(decode(w), 'SYSMES') != w:
            sys.exit('SYSMES.ALD: decode/encode is not lossless')
    r = rebuild_sysmes(d, a, b)
    ri, rs = sysmes_tables(r)
    if read_table(r, ri, len(a)) != a or read_table(r, rs, len(b)) != b:
        sys.exit('SYSMES.ALD: rebuilt file differs')
    print('ok: %d mensagens de salas, %d itens, %d mensagens de sistema' % (total, len(a), len(b)))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--iso')
    sub = p.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export')
    e.add_argument('--out', default='translation')
    i = sub.add_parser('import')
    i.add_argument('--in', dest='inp', default='translation')
    i.add_argument('--mods', default='mods')
    sub.add_parser('check')
    args = p.parse_args()
    {'export': cmd_export, 'import': cmd_import, 'check': cmd_check}[args.cmd](args)


if __name__ == '__main__':
    main()
