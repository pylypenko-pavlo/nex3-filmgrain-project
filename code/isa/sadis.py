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
# Decoder follows ma1co/SA-DSP dsp.slaspec (github.com/ma1co/SA-DSP, 2021-08-09, 322bc4a):
# rd=[3:0] (dest / store base), rs=[7:4] (source / store value); flag 'fr'; no delay slots.
# Local additions (not in ma1co): 0009 (engine launch, r0 = command table), 000a (seen as function prefix).
R=lambda i: 'sp' if i==15 else f'r{i}'
OP16={0x0000:'nop',0x0001:'cfr',0x0002:'sfr',0x0003:'ret',0x0004:'wfi',
      0x0009:'run_engine r0   ; local, not in ma1co',0x000a:'op000a ; local, unknown'}
OP12={0x002:'mov {d},fr',0x003:'mov {d},pc',0x005:'rlxs {d}',0x006:'rrxs {d}',0x007:'lsls {d},#1',
      0x008:'asrs {d},#1',0x009:'cmp.gts {d},#0',0x00a:'b {d}',0x00b:'bl {d}',
      0x00c:'ldr lr,[{d}],#4',0x00d:'str lr,[{d},#-4]!'}
OP8={0x01:'ldrsb {d},[{s}]',0x02:'ldrsb {d},[{s},r0]',0x03:'ldrsb {d},[{s}],#1',
     0x04:'ldrb {d},[{s}]',0x05:'ldrb {d},[{s},r0]',0x06:'ldrb {d},[{s}],#1',
     0x07:'ldrh {d},[{s}]',0x08:'ldrh {d},[{s},r0]',0x09:'ldrh {d},[{s}],#2',
     0x0a:'ldr {d},[{s}]',0x0b:'ldr {d},[{s},r0]',0x0c:'ldr {d},[{s}],#4',
     0x0d:'strb {s},[{d}]',0x0e:'strb {s},[{d},r0]',0x0f:'strb {s},[{d}],#1',0x10:'strb {s},[{d},#-1]!',
     0x11:'strh {s},[{d}]',0x12:'strh {s},[{d},r0]',0x13:'strh {s},[{d}],#2',0x14:'strh {s},[{d},#-2]!',
     0x15:'str {s},[{d}]',0x16:'str {s},[{d},r0]',0x17:'str {s},[{d}],#4',0x18:'str {s},[{d},#-4]!',
     0x19:'sxtb {d},{s}',0x1a:'sxth {d},{s}',0x1b:'mov {d},{s}',0x1c:'uxtb {d},{s}',0x1d:'uxth {d},{s}',
     0x1e:'add {d},{s}',0x1f:'adcs {d},{s}',0x20:'sub {d},{s}',0x21:'sbcs {d},{s}',0x22:'mul {d},{s}',
     0x23:'and {d},{s}',0x24:'orr {d},{s}',0x25:'mvn {d},{s}',0x26:'eor {d},{s}',0x27:'neg {d},{s}',
     0x28:'ngcs {d},{s}',0x29:'lsl {d},{s}',0x2a:'lsr {d},{s}',0x2b:'asr {d},{s}',
     0x2e:'cmp.eq {d},{s}',0x2f:'cmp.geu {d},{s}',0x30:'cmp.ges {d},{s}',0x31:'cmp.gtu {d},{s}',
     0x32:'cmp.gts {d},{s}',0x33:'cmp.nand {d},{s}',0x34:'fadd {d},{s}',0x35:'fsub {d},{s}',
     0x36:'fmul {d},{s}',0x37:'fdiv {d},{s}',0x38:'ftosi {d},{s}',0x39:'fsito {d},{s}'}
def dis1(m,a,pools):
    h=m.h(a); op4=h>>12; d=R(h&15); s=R((h>>4)&15); i8=(h>>4)&0xff
    if h in OP16: return OP16[h]
    if (h>>4) in OP12: return OP12[h>>4].format(d=d)
    if (h>>8) in OP8: return OP8[h>>8].format(d=d,s=s)
    if op4==4:
        t=(a&~1)+4+2*i8; v=(m.t[t]|m.t[t+1]<<8) if t+2<=len(m.t) else None
        return f'ldrh {d},[pc,#{2*i8}]   ; @{t:#x}' + (f' ={v:#06x}' if v is not None else '')
    if op4==5:
        t=(a&~3)+4+4*i8; v=m.w32(t) if t+4<=len(m.t) else None
        return f'ldr {d},[pc,#{4*i8}]    ; @{t:#x}' + (f' ={v:#x}' if v is not None else '')
    if op4==6: return f'ldr {d},[{s},#{4*((h>>8)&15)}]'
    if op4==7: return f'str {s},[{d},#{4*((h>>8)&15)}]'
    if op4==8: return f'cmp.eq {d},#{sx(i8,8)}'
    if op4==9: return f'mov {d},#{sx(i8,8)}'
    if op4==0xa: return f'add {d},#{sx(i8,8)}'
    t=a+4+2*sx(h&0xfff,12)
    if op4==0xb: return f'b {t:#x}'
    if op4==0xc: return f'bfs {t:#x}       ; branch if fr set'
    if op4==0xd: return f'bfc {t:#x}       ; branch if fr clear'
    if (h>>9)==0x78: return f'lsl {d},#{(h>>4)&31}'
    if (h>>9)==0x79: return f'lsr {d},#{(h>>4)&31}'
    if (h>>9)==0x7a: return f'asr {d},#{(h>>4)&31}'
    return f'.half {h:#06x}   ; undefined in ma1co spec'
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
