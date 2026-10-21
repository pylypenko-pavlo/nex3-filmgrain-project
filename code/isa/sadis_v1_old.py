#!/usr/bin/env python3
"""Partial disassembler for Sony BIONZ SA-DSP scalar (16-bit, SH-like) code.
Usage: sadis.py <module.bin> [start end] [--img N]
Addresses are text-relative (file offset - (desc + desc.w[12]))."""
import sys,struct
sys.path.insert(0,__import__('os').path.dirname(__file__))
from mod import Mod,lits
def sx(v,b): return v-(1<<b) if v>>(b-1)&1 else v
R=lambda i: 'sp' if i==15 else f'r{i}'
OP00={0x0:'nop',0x3:'rts',0x4:'sleep',0x9:'run_engine(r0)',0xa:'op000a'}
SUB00={0x7:'shll(T)? {r}',0x8:'shlr? {r}',0xa:'jmp @{r}',0xb:'jsr @{r}',0xc:'lds.l @{r}+,pr',0xd:'sts.l pr,@-{r}'}
# reg-reg ops: high byte = opcode, [7:4]=Rm (source/base), [3:0]=Rn (dest; base for stores)
RR={0x18:'mov.l {m},@-{n}',0x0c:'mov.l @{m}+,{n}',0x1b:'mov {m},{n}',
    0x0a:'mov.l @{m},{n}',0x0b:'mov.l @(r0,{m}),{n}',0x08:'mov.w @(r0,{m}),{n}',0x22:'mul {m},{n}',0x26:'xor? {m},{n}',0x25:'not? {m},{n}',0x1d:'exts.w? {m},{n}',0x15:'mov.l {n_},@{m_}',0x07:'mov.w? @{m},{n}',0x09:'mov.w? @{m}+,{n}',
    0x1e:'add {m},{n}',0x20:'sub {m},{n}',0x23:'and {m},{n}',0x24:'or {m},{n}',0x27:'neg {m},{n}',
    0x2e:'cmp/? {m},{n}',0x30:'cmp/gt? {m},{n}',0x32:'cmp/hs? {m},{n}',0x29:'shl? {m},{n}',
    0x01:'mov.w? @{m},{n}',0x0d:'mov.w? {n_},@{m_}',0x16:'mov.l {m},@(r0,{n})',0x1c:'extu.w? {m},{n}',0x21:'subc? {m},{n}'}
def dis1(m,a,pools):
    h=m.h(a); op=h>>12; x=(h>>8)&0xf; y=(h>>4)&0xf; z=h&0xf; i8=(h>>4)&0xff
    if h>>8==0:
        if h in OP00: return OP00[h]
        if y in SUB00: return SUB00[y].format(r=R(z))
        return f'.op00 {h:04x}'
    if op==5:
        t=(a&~3)+4+4*i8; v=m.w32(t) if t+4<=len(m.t) else None
        return f'mov.l @({t:#x}),{R(z)}    ; ={v:#x}' if v is not None else f'mov.l @({t:#x}),{R(z)}'
    if op==4:
        t=a+4+2*i8; v=m.t[t]|m.t[t+1]<<8 if t+2<=len(m.t) else None
        return f'mov.w @({t:#x}),{R(z)}    ; ={v:#06x}' if v is not None else f'mov.w @({t:#x}),{R(z)}'
    if op==9: return f'mov #{sx(i8,8)},{R(z)}'
    if op==0xa: return f'add #{sx(i8,8)},{R(z)}'
    if op==8: return f'cmp?/eq #{sx(i8,8)},{R(z)}'
    if op==0xb: return f'bra {a+4+2*sx(h&0xfff,12):#x}'
    if op==0xc: return f'bf {a+4+2*sx(h&0xfff,12):#x}'
    if op==0xd: return f'bt {a+4+2*sx(h&0xfff,12):#x}'
    if op==6: return f'mov.l @({4*x},{R(y)}),{R(z)}'
    if op==7: return f'mov.l {R(y)},@({4*x},{R(z)})'
    if op==0xf and x in (0,1,2,3): return ['shll?','shlr?','shll16+?','shlr16+?'][x]+f' #{y},{R(z)}'
    if h>>8 in RR: return RR[h>>8].format(m=R(y),n=R(z),m_=R(z),n_=R(y))
    return f'.op{h>>8:02x} {R(y)},{R(z)}'
def run(m,s,e):
    pools=set()
    for a,r,t,v in lits(m):
        if s<=a<e and t>a: pools.add(t)
    a=s
    while a<e:
        if a in pools:
            print(f'{a:6x}:  .long {m.w32(a):#010x}'); a+=4; continue
        if a%8==0 and m.t[a:a+8]==bytes.fromhex('f7e13edc87fb701f'):
            print(f'{a:6x}:  .vliw64 nop'); a+=8; continue
        print(f'{a:6x}:  {m.h(a):04x}  {dis1(m,a,pools)}'); a+=2
def _main():
    img=0
    if '--img' in sys.argv: i=sys.argv.index('--img'); img=int(sys.argv[i+1]); del sys.argv[i:i+2]
    m=Mod(sys.argv[1],d=__import__('os').path.dirname(sys.argv[1]) or '.',img=img) if '/' in sys.argv[1] else Mod(sys.argv[1],img=img)
    s=int(sys.argv[2],0) if len(sys.argv)>2 else 0; e=int(sys.argv[3],0) if len(sys.argv)>3 else len(m.t)
    run(m,s,e)
if __name__=='__main__':
    import os
    if '--desc' in sys.argv:
        i=sys.argv.index('--desc'); d=int(sys.argv[i+1],0); del sys.argv[i:i+2]
        from mod import ModAt
        m=ModAt(os.path.expanduser(sys.argv[1]),d)
        s=int(sys.argv[2],0) if len(sys.argv)>2 else 0; e=int(sys.argv[3],0) if len(sys.argv)>3 else len(m.t)
        print(f'# desc@{d:#x} tbase(file)={m.tbase:#x} textlen={len(m.t):#x}'); run(m,s,e)
    else: _main()
