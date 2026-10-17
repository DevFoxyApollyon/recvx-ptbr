#!/usr/bin/env python3
"""Subtitle file helper (docs/SUBTITLES.md).

  subtitles.py template [--iso ISO] [--out mods/legendas.txt]

Writes a legendas.txt skeleton with one [VOICEn.AFS/id] block per voiced line of the disc and
its length, ready to be filled in. Existing blocks of the output file are kept (only missing
lines are added), so it can be run again safely. The skeleton holds no game text; what you
write into it is your own translation and stays in the ignored mods/ folder.
"""
import argparse, os, re, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdx  # noqa: E402

ARCHIVES = ('VOICE1.AFS', 'VOICE2.AFS')


def adx_length(head):
    if len(head) < 16 or head[0] != 0x80:
        return None
    rate, total = struct.unpack_from('>II', head, 8)
    return total / rate if rate else None


def existing_keys(path):
    if not os.path.exists(path):
        return set()
    keys = set()
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'\s*\[([^\]]+)\]', line)
        if m:
            keys.add(m.group(1).strip().upper())
    return keys


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('cmd', choices=['template'])
    p.add_argument('--iso')
    p.add_argument('--out', default=os.path.join('mods', 'legendas.txt'))
    args = p.parse_args()
    iso_path = args.iso or os.environ.get('RECVX_ISO')
    if not iso_path or not os.path.exists(iso_path):
        sys.exit('disc image not found: pass --iso or set RECVX_ISO')
    iso = rdx.Iso(iso_path)
    have = existing_keys(args.out)
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    new = os.path.exists(args.out)
    added = 0
    with open(args.out, 'a', encoding='utf-8', newline='\n') as f:
        if not new:
            f.write('# Legendas das falas (docs/SUBTITLES.md). Um bloco por fala: [ARQUIVO/numero].\n'
                    '# Escreva o texto embaixo do bloco. Para trocar de frase no meio da fala, comece a linha\n'
                    '# com o tempo em segundos (ex.: 2.5 Texto). | quebra a linha na tela.\n'
                    '# Ligue "Mostrar codigo das falas" (F1 > Audio) para ver o codigo de cada fala no jogo.\n\n')
        for name in ARCHIVES:
            afs = rdx.Afs(iso, name)
            for i in range(len(afs.toc)):
                key = '%s/%d' % (name, i)
                if key in have:
                    continue
                o, s = afs.toc[i]
                iso.f.seek(afs.lsn * rdx.SECTOR + o)
                length = adx_length(iso.f.read(32))
                if length is None:
                    continue
                f.write('[%s]  # %.1f s\n\n' % (key, length))
                added += 1
    print('%d falas adicionadas em %s' % (added, args.out))


if __name__ == '__main__':
    main()
