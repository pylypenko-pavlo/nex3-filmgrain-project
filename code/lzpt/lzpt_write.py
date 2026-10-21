#!/usr/bin/env python3
"""LZPT ('TPZL') image writer for Sony CXD4132-era cameras.

Format (derived from fwtool/archive/lzpt.py + lz77 inflater, and from the
original NEX-3N p3/p8 images):

  header  : 'TPZL', u32 blockSize(log2, =16), u32 tocOffset(=0x18), u32 tocSize,
            then 8 zero bytes (pad up to tocOffset)
  toc     : nBlocks x (u32 offset, u32 size), offsets absolute; blocks follow the
            toc back-to-back, no gaps
  block   : 64 KiB of input = 16 independent sub-streams of 4 KiB each, block
            size padded with 0x00 to a multiple of 4 (pad is NOT in toc size? -> it IS)
  substream (stored): 0x0f, 0x00, u16 len, raw bytes
  substream (lz77)  : 0xf0, then groups: flag byte (LSB first, 1 = match) + 8 items;
            literal = 1 byte; match = 2 bytes: hi nibble = length code
            (0..13 -> 3..16, 14 -> 32, 15 -> 64), 12-bit distance (1..4095);
            distance 0 = end marker. Window = current sub-stream only.
  match finder of the original Sony tool (verified 100% on samples):
            candidates = earlier positions with equal 3-byte prefix, nearest
            first; keep strictly longest (raw length capped at 64); stop as soon
            as a candidate reaches raw length >= 8. Raw length L is coded as the
            largest code <= L (17..31 -> 16, 33..63 -> 32).
  image tail: 0xFF up to the partition size when writing a raw partition image.
"""
import struct
import sys
from multiprocessing import Pool

BLOCK_LOG2 = 16
SUB = 4096
TOC_OFFSET = 0x18
LEN_CODES = list(range(3, 17)) + [32, 64]


def code_len(l):
    if l >= 64:
        return 64, 15
    if l >= 32:
        return 32, 14
    if l >= 16:
        return 16, 13
    return l, l - 3


def lz_sub(data, nice=8):
    n = len(data)
    heads = {}
    out = bytearray(b'\xf0')
    flagpos = len(out); out.append(0); bit = 0; flags = 0
    pos = 0

    def item_done(is_match):
        nonlocal bit, flags, flagpos
        if is_match:
            flags |= 1 << bit
        bit += 1
        if bit == 8:
            out[flagpos] = flags
            flagpos = len(out); out.append(0); bit = 0; flags = 0

    while pos < n:
        bestl = 0; bestd = 0
        if pos + 3 <= n:
            key = data[pos:pos + 3]
            lst = heads.get(key)
            if lst:
                maxl = min(64, n - pos)
                for cpos in reversed(lst):
                    dist = pos - cpos
                    if dist > 4095:
                        break
                    l = 3
                    while l < maxl and data[cpos + l] == data[pos + l]:
                        l += 1
                    if l > bestl:
                        bestl = l; bestd = dist
                    if l >= nice:
                        break
        if bestl >= 3:
            l, c = code_len(bestl)
            out.append(c << 4 | bestd >> 8); out.append(bestd & 0xff)
            item_done(True)
            for p in range(pos, pos + l):
                if p + 3 <= n:
                    heads.setdefault(data[p:p + 3], []).append(p)
            pos += l
        else:
            out.append(data[pos])
            item_done(False)
            if pos + 3 <= n:
                heads.setdefault(data[pos:pos + 3], []).append(pos)
            pos += 1
    # end marker
    out.append(0); out.append(0)
    item_done(True)
    if bit != 0:
        out[flagpos] = flags
    else:
        del out[flagpos]  # unused trailing flag byte
    return bytes(out)


def stored_sub(data):
    return b'\x0f\x00' + struct.pack('<H', len(data)) + data


def compress_block(block):
    out = bytearray()
    for i in range(0, len(block), SUB):
        sub = block[i:i + SUB]
        c = lz_sub(sub)
        out += c if len(c) <= len(sub) else stored_sub(sub)  # verified: 4098-byte LZ -> stored
    pad = -len(out) % 4
    return bytes(out) + b'\x00' * pad, pad


def write_lzpt(raw, procs=None):
    bsz = 1 << BLOCK_LOG2
    assert len(raw) % bsz == 0, 'input must be a multiple of 64 KiB'
    blocks = [raw[i:i + bsz] for i in range(0, len(raw), bsz)]
    with Pool(procs) as p:
        comp = p.map(compress_block, blocks, chunksize=8)
    toc_size = 8 * len(comp)
    hdr = b'TPZL' + struct.pack('<III', BLOCK_LOG2, TOC_OFFSET, toc_size) + b'\x00' * (TOC_OFFSET - 16)
    off = TOC_OFFSET + toc_size
    toc = bytearray()
    for c, _ in comp:
        toc += struct.pack('<II', off, len(c)); off += len(c)
    body = b''.join(c for c, _ in comp)
    # Sony's tool does not write the zero pad of the LAST block (toc size still
    # includes it); on flash those bytes read as 0xFF. Reproduce that.
    lastpad = comp[-1][1]
    if lastpad:
        body = body[:-lastpad]
    return hdr + bytes(toc) + body


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('infile'); ap.add_argument('outfile')
    ap.add_argument('--pad', type=lambda x: int(x, 0), help='pad with 0xFF to this size (partition size)')
    a = ap.parse_args()
    raw = open(a.infile, 'rb').read()
    img = write_lzpt(raw)
    if a.pad:
        if len(img) > a.pad:
            sys.exit('ERROR: image %d > partition %d' % (len(img), a.pad))
        img += b'\xff' * (a.pad - len(img))
    open(a.outfile, 'wb').write(img)
    print('wrote', a.outfile, len(img), 'bytes')


if __name__ == '__main__':
    main()
