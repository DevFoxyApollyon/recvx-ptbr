#!/usr/bin/env python3
"""Wrap the translatable string literals of C/C++ sources in L(...) (PT-BR fork).

  lang_wrap.py FILE...

A literal (adjacent literals joined) is wrapped when lang_ptbr.inc has it, it is not on a
preprocessor line, not already inside L( and not part of an initializer (those are translated
where they are drawn). Comments and char literals are skipped by a small tokenizer.
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lang_extract  # noqa: E402

BS = chr(92)  # backslash


def tokens(s):
    """(start, end, content) of every string literal, outside comments and char literals"""
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if s.startswith('//', i):
            i = s.find('\n', i)
            i = n if i < 0 else i
        elif s.startswith('/*', i):
            j = s.find('*/', i + 2)
            i = n if j < 0 else j + 2
        elif c in ('"', "'"):
            j = i + 1
            while j < n and s[j] != c:
                j += 2 if s[j] == BS else 1
            if c == '"':
                yield i, j + 1, s[i + 1:j]
            i = j + 1
        else:
            i += 1


def wrap(path, table):
    s = open(path, encoding='utf-8', newline='').read()
    groups, cur = [], None
    for a, b, text in tokens(s):
        if cur and s[cur[1]:a].strip() == '':
            cur = (cur[0], b, cur[2] + text)
        else:
            if cur:
                groups.append(cur)
            cur = (a, b, text)
    if cur:
        groups.append(cur)
    out, last, n = [], 0, 0
    for a, b, text in groups:
        line = s[s.rfind('\n', 0, a) + 1:a]
        if text not in table or line.lstrip().startswith('#'):
            continue
        if re.search(r'\bL\(\s*$', s[max(0, a - 8):a]):
            continue
        if re.match(r'\s*(static\s+)?const\s+char\s*\*', line) or re.match(r'\s*\{\s*$', line) or re.match(r'\s*\[\w+\]\s*=', line):
            continue
        out.append(s[last:a])
        out.append('L(' + s[a:b] + ')')
        last = b
        n += 1
    out.append(s[last:])
    open(path, 'w', encoding='utf-8', newline='').write(''.join(out))
    return n


def main():
    table = lang_extract.table()
    for p in sys.argv[1:]:
        print(p, 'wrapped', wrap(p, table))


if __name__ == '__main__':
    main()
