"""Run av-cam Create3DLUT (file 0x3d03c4, Thumb) under unicorn with stubbed structures.

Purpose: verify what the function does with its inputs. Findings are in notes/simulator.md (part B).
Inputs are synthetic (the real RefAdr table and the runtime structure are not known); this is a semantic probe,
not a reconstruction of the camera's LUT for a given Backup block.
"""
import struct
import sys

import numpy as np
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

AV = __import__('os').environ['NEX3N_AVCAM']
BASE = 0xc3441000
FUNC = 0x3d03c4
LOG_FUNCS = (0x3d0320, 0x230ad6)
RET = 0x0FFF0000

A, P0, P00, P8, REF, BUF, STK = 0x20000000, 0x20001000, 0x20002000, 0x20003000, 0x20004000, 0x20010000, 0x10100000


def run(ref, level=0, mode=1, convsd=0, ipflag=0, sector=(0, 0, 0, 0, 0, 0), idx=0, blk_cr=0, blk_cb=0):
    """ref: int8 array (3, 5, 9, 9) = planes at +0, +0x195, +0x32a. Returns decoded (3, 5, 9, 9) from BufAdr."""
    d = open(AV, 'rb').read()
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    size = (len(d) + 0xfff) & ~0xfff
    mu.mem_map(BASE, size); mu.mem_write(BASE, d)
    mu.mem_map(0x20000000, 0x40000); mu.mem_map(STK - 0x10000, 0x20000); mu.mem_map(RET, 0x1000)
    mu.mem_write(RET, b'\x00\xbf' * 8)
    w32 = lambda a, v: mu.mem_write(a, struct.pack('<I', v & 0xffffffff))
    w8 = lambda a, v: mu.mem_write(a, struct.pack('<B', v & 0xff))
    w16 = lambda a, v: mu.mem_write(a, struct.pack('<h', v))
    w32(A + 0, P0); w32(A + 8, P8); w32(A + 0xc, BUF)
    w32(P0 + 0, P00); w8(P0 + 4, idx); w8(P0 + 6, 0); w8(P0 + 0x20 + 7, level); w8(P0 + 0x20 + 0xd, ipflag)
    w8(P0 + 0x20 + 0x15, 0)
    w8(P00 + 0x300, 0x08 if (blk_cr or blk_cb) else 0)
    w8(P00 + 0x5c0, ((blk_cr & 0xf) << 4) | (blk_cb & 0xf))
    w8(P8 + 2, 0); w32(P8 + 0xa0, REF); w8(P8 + 0xa4, mode); w8(P8 + 0xa5, convsd)
    mu.mem_write(REF, np.asarray(ref, np.int8).reshape(3, -1).tobytes())
    # per-node 'ip' offsets: int16 pairs at BUF+0x83e+2*flag and BUF+0x840+2*flag (flag 0..5)
    for k, v in enumerate(sector):
        w16(BUF + 0x83e + 2 * k, int(v))
    w16(BUF + 0x84a, int(sector[0]))  # wrap entry, as the caller (0x3d0aa6) copies it
    sp = STK
    mu.reg_write(UC_ARM_REG_SP, sp); mu.reg_write(UC_ARM_REG_R0, A); mu.reg_write(UC_ARM_REG_LR, RET | 1)

    def hook(uc, addr, sz, _):
        off = addr - BASE
        if off in LOG_FUNCS:
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    mu.hook_add(UC_HOOK_CODE, hook)
    mu.emu_start((BASE + FUNC) | 1, RET, count=2_000_000)
    buf = BUF + idx * 0x654 + 0x864
    # scatter order: HW word index = table[0xa2*r0 + 18*i + 2*j] at 0xc3a1852e (see disassembly 0x3d0918)
    scat = np.frombuffer(d, '<u2', 0x400, 0xc3a1852e - BASE)
    out = np.zeros((3, 5, 9, 9), int)
    for r0 in range(5):
        for i in range(9):
            for j in range(9):
                k = int(scat[(0xa2 * r0 + 18 * i + 2 * j) // 2])
                wv = struct.unpack('<I', mu.mem_read(buf + 4 * k, 4))[0]
                f = [(wv >> 16) & 0x7f, (wv >> 8) & 0x7f, wv & 0x7f]  # three 7-bit two's-complement fields
                f = [v - 128 if v >= 64 else v for v in f]
                out[:, r0, i, j] = f
    return out


if __name__ == '__main__':
    rng = np.random.default_rng(0)
    ref = rng.integers(-60, 60, (3, 5, 9, 9))
    full = run(ref)
    print('level 0 (full): max |out - ref| per plane:', [int(np.abs(full[p] - ref[p]).max()) for p in range(3)])
    for lv in (2, 4, 6):
        o = run(ref, level=lv)
        k = [np.polyfit(ref[p].ravel(), o[p].ravel(), 1)[0] for p in range(3)]
        print('level %d: fitted gain per plane %s (expect %.3f)' % (lv, np.round(k, 3), lv / 8))
    z = np.zeros((3, 5, 9, 9), int)
    o = run(z, ipflag=1, sector=(40, -40, 20, -20, 10, -10))
    print('zero ref + 6 sector offsets: plane0 at Y=2 (9x9 CbCr):\n', o[0, 2])
    print('planes 1,2 untouched:', int(np.abs(o[1:]).max()))
    sys.exit(0)
