# Generate the injected grain routine source for a given amplitude N / mask,
# placed at file offset ORG in core0, returning to BACK (core0 chunk+0x2fc = 0xaf4c).
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from saasm import asm
def routine_src(N, mask):
    return f"""
grain:
    add  sp,#0x50          ; displaced hook-site instruction (epilogue add sp,#0x50)
    mov  r0,#1
    lsl  r0,#11            ; r0 = 0x800 (tile size, 128x8 YUYV)
    mov  r1,r13            ; r1 = engine window = end-of-tile pointer
    sub  r1,r0             ; r1 = tile top-left = window - 0x800
    mov  r3,r1             ; r3 = LFSR state, seeded per-tile from tile address
loop:
    cmp.gtu r13,r1         ; fr = (end > ptr) : luma remaining
    bfc  done
    mov  r2,r3             ; --- xorshift32: x^=x<<13; x^=x>>17; x^=x<<5 ---
    lsl  r2,#13
    eor  r3,r2
    mov  r2,r3
    lsr  r2,#17
    eor  r3,r2
    mov  r2,r3
    lsl  r2,#5
    eor  r3,r2
    mov  r4,r3             ; --- noise = (lfsr & mask) - N ---
    mov  r0,#{mask}
    and  r4,r0
    mov  r0,#{N}
    sub  r4,r0            ; r4 = signed noise in ~[-N, +N]
    ldrb r5,[r1]          ; r5 = Y (luma, even byte)
    add  r5,r4            ; Y + noise
    mov  r0,#0            ; clamp low -> 0
    cmp.ges r5,r0
    bfs  chkhi
    mov  r5,r0
chkhi:
    mov  r0,#-1           ; r0 = 255
    uxtb r0,r0
    cmp.gts r5,r0         ; clamp high -> 255
    bfc  store
    mov  r5,r0
store:
    strb r5,[r1]          ; write luma (chroma/odd bytes untouched)
    add  r1,#2            ; next Y (skip chroma)
    b    loop
done:
    b    0xaf4c           ; return into the stock epilogue (add sp,#0x40; pops; ret)
"""
if __name__=='__main__':
    N=int(sys.argv[1]); mask=int(sys.argv[2]); org=int(sys.argv[3],0)
    src=routine_src(N,mask).splitlines()
    out,labels=asm(src,org)
    import struct
    bs=bytearray()
    for a,h in out: bs+=struct.pack('<H',h)
    sys.stdout.write(bs.hex())
    sys.stderr.write(f"N={N} mask={mask} org={org:#x} len={len(bs)} labels={ {k:hex(v) for k,v in labels.items()} }\n")
