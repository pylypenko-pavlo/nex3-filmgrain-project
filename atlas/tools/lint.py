#!/usr/bin/env python3
"""Atlas linter: schema fields, statuses, evidence, scope, cross-references.
Usage: python3 atlas/tools/lint.py [--strict]   (exit 1 on errors)"""
import re, sys, glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = sorted(glob.glob(os.path.join(ROOT, '0[1-9]*.md')))
STATUSES = {'verified-hw', 'verified-code', 'hypothesis', 'refuted', 'unknown'}
SCOPES = {'nex3n-fw1.00', 'CXD4132', 'SA-platform', 'unknown'}
REQ = ('status', 'evidence', 'source', 'date')
strict = '--strict' in sys.argv
errs, warns = [], []
defs, recs = {}, []
for p in PAGES:
    name = os.path.basename(p)
    text = open(p).read()
    for m in re.finditer(r'^### ((?:C-[A-Z]+-\d{3})|(?:E-\d{4})|(?:G-\d{3}))\b[^\n]*\n((?:- [^\n]*\n|  [^\n]*\n)*)', text, re.M):
        rid, body = m.group(1), m.group(2)
        if rid in defs: errs.append(f'{name}: duplicate id {rid} (also in {defs[rid]})')
        defs[rid] = name
        if rid.startswith('C-'): recs.append((name, rid, body))
for name, rid, body in recs:
    f = dict(re.findall(r'^- (\w+):\s*(.*)$', body, re.M))
    for k in REQ:
        if k not in f or not f[k].strip(): errs.append(f'{name}: {rid} missing field {k}')
    st = f.get('status', '').split()[0] if f.get('status') else ''
    if st and st not in STATUSES: errs.append(f'{name}: {rid} bad status "{st}"')
    sc = f.get('scope', '').split()[0] if f.get('scope') else ''
    if not sc: (errs if strict else warns).append(f'{name}: {rid} missing scope')
    elif sc not in SCOPES: errs.append(f'{name}: {rid} bad scope "{sc}"')
    ev = f.get('evidence', '')
    if st == 'verified-hw' and not re.search(r'E-\d{4}|live|photo|frame|DSC\d+|measured|dump|log|MATCH|observed|shot|on camera|flash', ev, re.I):
        errs.append(f'{name}: {rid} verified-hw without experiment/observation in evidence')
    if st == 'verified-code' and not re.search(r'0x[0-9a-f]+|\.bin|\.so|\.elf|\.py|\.ko|offset|table|disasm|scan|C-[A-Z]+-\d{3}|\b\d+/\d+\b|header|string|literal|xref|emulat|decode', ev, re.I):
        errs.append(f'{name}: {rid} verified-code without address/file in evidence')
    if re.match(r'\s*(a )?notes?\b[;,. ]', ev, re.I) and st.startswith('verified'):
        errs.append(f'{name}: {rid} evidence is only a note but status {st}')
for p in PAGES:
    name = os.path.basename(p)
    for i, line in enumerate(open(p), 1):
        if re.match(r'\|\s*`?[A-HLR]-[A-Z]+-\d{3}', line) or 'extract' in line.lower(): continue
        for r in re.findall(r'\b(C-[A-Z]+-\d{3}|E-\d{4})\b', line):
            if r not in defs: errs.append(f'{name}:{i}: dangling reference {r}')
        for r in re.findall(r'tmp:[A-Z]-[A-Z]+-\d{3}', line):
            warns.append(f'{name}:{i}: unresolved temporary id {r}')
from collections import Counter
c = Counter()
for name, rid, body in recs:
    m = re.search(r'^- status:\s*(\S+)', body, re.M); c[m.group(1) if m else '?'] += 1
print(f'records: {len(recs)} claims, {sum(1 for d in defs if d.startswith("E-"))} experiments; status: {dict(c)}')
for w in warns[:50]: print('WARN', w)
if len(warns) > 50: print(f'WARN ... {len(warns)-50} more')
for e in errs[:80]: print('ERR ', e)
if len(errs) > 80: print(f'ERR  ... {len(errs)-80} more')
print(f'{len(errs)} errors, {len(warns)} warnings')
sys.exit(1 if errs else 0)
