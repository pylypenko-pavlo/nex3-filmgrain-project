#!/usr/bin/env python3
"""Slot view of 64-bit VLIW bundles in a Sony SA module.
Usage: vdump.py <module.bin> [file_start file_end]
Default: every run that contains the NOP bundle 0x1f70fb87dc3ee1f7.
Bundle = S0[63:52] (12 bit) + S1[51:39] S2[38:26] S3[25:13] S4[12:0] (13 bit each).
13-bit slot printed as op3.a5.b5 (hypothesis: op[12:10], a[9:5], b[4:0]); idle slot = 0x1f7 ('.')."""
import sys,struct
from slots import slots,NOP
def s13(v):
    if v==0x1f7: return '    .    '
    if v==0x1fff: return '  ffff   '
    return f'{v>>10}.{(v>>5)&31:02d}.{v&31:02d}  '
def main():
    b=open(sys.argv[1],'rb').read()
    if len(sys.argv)>3: s,e=int(sys.argv[2],0),int(sys.argv[3],0)
    else:
        nb=struct.pack('<Q',NOP); i=b.find(nb)
        if i<0: print('no VLIW NOP in file'); return
        s=i&~7; e=b.rfind(nb)+8
    for o in range(s&~7,e,8):
        w=struct.unpack_from('<Q',b,o)[0]; sl=slots(w)
        tag='NOP' if w==NOP else ''
        s0='  .  ' if sl[0]==0x1f7 else f'{sl[0]:03x}  '
        print(f'{o:06x} {w:016x}  S0={s0} '+' '.join(s13(x) for x in sl[1:]),tag)
if __name__=='__main__': main()
