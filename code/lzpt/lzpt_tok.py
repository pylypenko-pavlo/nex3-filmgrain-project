"""Helpers to tokenise original LZPT sub-streams (for format reverse engineering)."""
import struct

L = list(range(3, 17)) + [32, 64]


def parse_header(d):
    mag, bs, to, ts = struct.unpack('<4sIII', d[:16])
    toc = [struct.unpack('<II', d[to + i:to + i + 8]) for i in range(0, ts, 8)]
    return bs, to, ts, toc


def substreams(d, off, bs=16):
    """yield (start, end, kind, tokens, outbytes) for each sub-stream of a block"""
    p = off; total = 0
    while total < (1 << bs):
        s = p
        if d[p] == 0x0f:
            l = d[p + 2] | d[p + 3] << 8
            out = d[p + 4:p + 4 + l]; p += 4 + l
            yield s, p, 'st', None, out
        else:
            p += 1; out = bytearray(); toks = []
            while True:
                fl = d[p]; p += 1; end = False
                for i in range(8):
                    if fl >> i & 1:
                        b0, b1 = d[p], d[p + 1]; p += 2
                        bd = (b0 & 15) << 8 | b1
                        if bd == 0:
                            end = True; toks.append(('end', i)); break
                        l = L[b0 >> 4]
                        for _ in range(l): out.append(out[-bd])
                        toks.append(('m', l, bd, b0 >> 4))
                    else:
                        out.append(d[p]); toks.append(('l', d[p])); p += 1
                if end: break
            yield s, p, 'lz', toks, bytes(out)
        total += len(out)
