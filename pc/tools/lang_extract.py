#!/usr/bin/env python3
"""List the port's menu strings and check the PT-BR table (pc/src/host/lang_ptbr.inc).

  lang_extract.py            # print strings that have no translation yet
  lang_extract.py --all      # print every candidate string

Candidates are the C string literals (adjacent literals joined) of the menu sources that look
like text for people (letters, not ini keys or file names). The table maps the English text to
Portuguese; lang.c L() looks it up at draw time.
"""
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCES = ['pc/src/host/settings.c', 'pc/src/host/overlay.cpp', 'pc/glue/options_glue.c',
           'pc/glue/lobby_glue.c', 'pc/src/input/bindings.c', 'pc/glue/cheat_glue.c']
TABLE = 'pc/src/host/lang_ptbr.inc'

LIT = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def strip_comments(s):
    return re.sub(r'//[^\n]*|/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), s, flags=re.S)


def literals(path):
    s = strip_comments(open(os.path.join(REPO, path), encoding='utf-8', errors='replace').read())
    out, cur, end = [], None, -1
    for m in LIT.finditer(s):
        if cur is not None and s[end:m.start()].strip() == '':
            cur += m.group(1)          # "a" "b" -> "ab"
        else:
            if cur is not None:
                out.append(cur)
            cur = m.group(1)
        end = m.end()
    if cur is not None:
        out.append(cur)
    return out


def is_ui(x):
    if not re.search(r'[A-Za-z]{2}', x):
        return False
    if re.fullmatch(r'[a-z0-9_./%:+\-]+', x):          # ini keys, file names, SDL names
        return False
    if x.startswith(('#', 'mods:', 'coop:', 'tps:', 'log:', 'gl:', 'room:')) or '\\n' == x:
        return False
    return True


def table():
    path = os.path.join(REPO, TABLE)
    if not os.path.exists(path):
        return {}
    s = open(path, encoding='utf-8').read()
    return {m.group(1): m.group(2) for m in re.finditer(r'\{\s*"((?:[^"\\]|\\.)*)"\s*,\s*"((?:[^"\\]|\\.)*)"\s*\}', s)}


def main():
    t = table()
    seen = []
    for f in SOURCES:
        for x in literals(f):
            if is_ui(x) and x not in seen:
                seen.append(x)
    todo = seen if '--all' in sys.argv else [x for x in seen if x not in t]
    for x in todo:
        print('"%s"' % x)
    print('# %d candidates, %d translated, %d to do' % (len(seen), sum(1 for x in seen if x in t), len([x for x in seen if x not in t])),
          file=sys.stderr)


if __name__ == '__main__':
    main()
