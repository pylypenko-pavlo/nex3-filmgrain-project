#!/usr/bin/env python3
"""Interpreter for the Sony SA-DSP scalar core (16-bit, ma1co SLEIGH semantics).
Goal: trace how a module's scalar code configures the VLIW engine - log every
store, especially to engine registers 0x40000+, and the r0 (command-table) value
at each `0009` run_engine. Pure emulation; no camera, no firmware changed.

Usage: saemu.py <module.bin> <desc_off> <entry_text> [--r4 V --r5 V --r6 V] [--steps N] [--trace]
Addresses printed are text-relative for code, absolute for data.
"""
import sys,struct,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from mod import ModAt

def sx(v,b): return v-(1<<b) if (v>>(b-1))&1 else v
def u32(v): return v & 0xffffffff

class Mem:
    """sparse byte memory; absolute addresses. default 0."""
    def __init__(s): s.b={}; s.writes=[]
    def r(s,a,n):
        v=0
        for i in range(n): v|=s.b.get(a+i,0)<<(8*i)
        return v
    def w(s,a,n,val,pc=None):
        for i in range(n): s.b[a+i]=(val>>(8*i))&0xff
        s.writes.append((pc,a,n,u32(val)))

class Emu:
    def __init__(s,mod,entry,r={},steps=200000,trace=False):
        s.m=mod; s.pc=entry; s.steps=steps; s.trace=trace
        s.R=[0]*16; s.lr=0xFFFFFFF0; s.fr=0
        s.R[15]=0x7000  # sp
        for k,v in r.items():
            if k=='sp': s.R[15]=v
            elif k=='lr': s.lr=v
            else: s.R[int(k[1:])]=v
        s.mem=Mem(); s.engine=[]  # (pc, reg_addr, value)
        s.cmdtables=[]            # (pc, r0) at run_engine
        s.log=[]
        s.stop=False
    def th(s,a):  # text halfword
        return s.m.t[a]|s.m.t[a+1]<<8 if 0<=a<len(s.m.t)-1 else 0
    def tw(s,a):  # text word (for PC-relative literal pool)
        return struct.unpack_from('<I',s.m.t,a)[0] if 0<=a<=len(s.m.t)-4 else 0
    def step(s):
        a=s.pc; h=s.th(a); op4=h>>12; rd=h&15; rs=(h>>4)&15; i8=(h>>4)&0xff
        nxt=a+2
        R=s.R
        def st(addr,n,val): s.mem.w(u32(addr),n,u32(val),a); rec(addr,val,n)
        def rec(addr,val,n):
            ad=u32(addr)
            if 0x40000<=ad<0x50000: s.engine.append((a,ad,u32(val)))
        # ---- 16-bit fixed ----
        if h==0x0000: pass
        elif h==0x0001: s.fr=0
        elif h==0x0002: s.fr=1
        elif h==0x0003:  # ret
            s.pc=s.lr
            if s.pc==0xFFFFFFF0: s.stop=True
            return
        elif h==0x0004: pass  # wfi
        elif h==0x0009:  # run_engine, r0 = command table ptr
            s.cmdtables.append((a,u32(R[0]))); s.log.append((a,'run_engine r0=%08x'%u32(R[0])))
        elif h==0x000a: pass
        # ---- op12 ----
        elif (h>>4)==0x002: R[rd]=s.fr
        elif (h>>4)==0x003: R[rd]=u32(a+4)
        elif (h>>4)==0x005:
            nf=(R[rd]>>31)&1; R[rd]=u32((R[rd]<<1)|s.fr); s.fr=nf
        elif (h>>4)==0x006:
            nf=R[rd]&1; R[rd]=(R[rd]>>1)|(s.fr<<31); s.fr=nf
        elif (h>>4)==0x007:
            s.fr=(R[rd]>>31)&1; R[rd]=u32(R[rd]<<1)
        elif (h>>4)==0x008:
            s.fr=R[rd]&1; R[rd]=u32(sx(R[rd],32)>>1)
        elif (h>>4)==0x009: s.fr=1 if sx(R[rd],32)>0 else 0
        elif (h>>4)==0x00a: s.pc=u32(R[rd]); return
        elif (h>>4)==0x00b:
            s.lr=u32(nxt); s.pc=u32(R[rd]); return
        elif (h>>4)==0x00c: s.lr=s.mem.r(R[rd],4); R[rd]=u32(R[rd]+4)
        elif (h>>4)==0x00d: R[rd]=u32(R[rd]-4); st(R[rd],4,s.lr)
        # ---- op8 two-reg ----
        elif (h>>8) in range(0x01,0x3a):
            o=h>>8
            if o==0x01: R[rd]=u32(sx(s.mem.r(R[rs],1),8))
            elif o==0x02: R[rd]=u32(sx(s.mem.r(R[rs]+R[0],1),8))
            elif o==0x03: R[rd]=u32(sx(s.mem.r(R[rs],1),8)); R[rs]=u32(R[rs]+1)
            elif o==0x04: R[rd]=s.mem.r(R[rs],1)
            elif o==0x05: R[rd]=s.mem.r(R[rs]+R[0],1)
            elif o==0x06: R[rd]=s.mem.r(R[rs],1); R[rs]=u32(R[rs]+1)
            elif o==0x07: R[rd]=u32(sx(s.mem.r(R[rs],2),16))
            elif o==0x08: R[rd]=u32(sx(s.mem.r(R[rs]+R[0],2),16))
            elif o==0x09: R[rd]=u32(sx(s.mem.r(R[rs],2),16)); R[rs]=u32(R[rs]+2)
            elif o==0x0a: R[rd]=s.mem.r(R[rs],4)
            elif o==0x0b: R[rd]=s.mem.r(R[rs]+R[0],4)
            elif o==0x0c: R[rd]=s.mem.r(R[rs],4); R[rs]=u32(R[rs]+4)
            elif o==0x0d: st(R[rd],1,R[rs]&0xff)
            elif o==0x0e: st(R[rd]+R[0],1,R[rs]&0xff)
            elif o==0x0f: st(R[rd],1,R[rs]&0xff); R[rd]=u32(R[rd]+1)
            elif o==0x10: R[rd]=u32(R[rd]-1); st(R[rd],1,R[rs]&0xff)
            elif o==0x11: st(R[rd],2,R[rs]&0xffff)
            elif o==0x12: st(R[rd]+R[0],2,R[rs]&0xffff)
            elif o==0x13: st(R[rd],2,R[rs]&0xffff); R[rd]=u32(R[rd]+2)
            elif o==0x14: R[rd]=u32(R[rd]-2); st(R[rd],2,R[rs]&0xffff)
            elif o==0x15: st(R[rd],4,R[rs])
            elif o==0x16: st(R[rd]+R[0],4,R[rs])
            elif o==0x17: st(R[rd],4,R[rs]); R[rd]=u32(R[rd]+4)
            elif o==0x18: R[rd]=u32(R[rd]-4); st(R[rd],4,R[rs])
            elif o==0x19: R[rd]=u32(sx(R[rs],8))
            elif o==0x1a: R[rd]=u32(sx(R[rs],16))
            elif o==0x1b: R[rd]=R[rs]
            elif o==0x1c: R[rd]=R[rs]&0xff
            elif o==0x1d: R[rd]=R[rs]&0xffff
            elif o==0x1e: R[rd]=u32(R[rd]+R[rs])
            elif o==0x1f:
                c=s.fr; res=R[rd]+R[rs]+c; s.fr=1 if res>0xffffffff else 0; R[rd]=u32(res)
            elif o==0x20: R[rd]=u32(R[rd]-R[rs])
            elif o==0x21:
                c=s.fr; res=R[rd]-R[rs]-c; s.fr=1 if res<0 else 0; R[rd]=u32(res)
            elif o==0x22: R[rd]=u32(R[rd]*R[rs])
            elif o==0x23: R[rd]=R[rd]&R[rs]
            elif o==0x24: R[rd]=R[rd]|R[rs]
            elif o==0x25: R[rd]=u32(~R[rs])
            elif o==0x26: R[rd]=R[rd]^R[rs]
            elif o==0x27: R[rd]=u32(-R[rs])
            elif o==0x28: R[rd]=u32(-R[rs]-s.fr)
            elif o==0x29: R[rd]=u32(R[rd]<<(R[rs]&31))
            elif o==0x2a: R[rd]=R[rd]>>(R[rs]&31)
            elif o==0x2b: R[rd]=u32(sx(R[rd],32)>>(R[rs]&31))
            elif o==0x2e: s.fr=1 if R[rd]==R[rs] else 0
            elif o==0x2f: s.fr=1 if R[rd]>=R[rs] else 0
            elif o==0x30: s.fr=1 if sx(R[rd],32)>=sx(R[rs],32) else 0
            elif o==0x31: s.fr=1 if R[rd]>R[rs] else 0
            elif o==0x32: s.fr=1 if sx(R[rd],32)>sx(R[rs],32) else 0
            elif o==0x33: s.fr=1 if (R[rd]&R[rs])==0 else 0
            elif 0x34<=o<=0x39: pass  # float ops: skip (not needed for engine-config trace)
            else: s.log.append((a,'unhandled op8 %02x'%o))
        # ---- op4 ----
        elif op4==4:  # ldrh rd,[pc,#2*i8] signed
            t=(a&~1)+4+2*i8; R[rd]=u32(sx(s.th(t),16))
        elif op4==5:  # ldr rd,[pc,#4*i8]
            t=(a&~3)+4+4*i8; R[rd]=s.tw(t)
        elif op4==6:  # ldr rd,[rs,#4*imm4]
            R[rd]=s.mem.r(R[rs]+4*((h>>8)&15),4)
        elif op4==7:  # str rs,[rd,#4*imm4]
            st(R[rd]+4*((h>>8)&15),4,R[rs])
        elif op4==8: s.fr=1 if R[rd]==u32(sx(i8,8)) else 0
        elif op4==9: R[rd]=u32(sx(i8,8))
        elif op4==0xa: R[rd]=u32(R[rd]+sx(i8,8))
        elif op4==0xb: s.pc=u32(a+4+2*sx(h&0xfff,12)); return
        elif op4==0xc:
            if s.fr: s.pc=u32(a+4+2*sx(h&0xfff,12)); return
        elif op4==0xd:
            if not s.fr: s.pc=u32(a+4+2*sx(h&0xfff,12)); return
        elif (h>>9)==0x78: R[rd]=u32(R[rd]<<((h>>4)&31))
        elif (h>>9)==0x79: R[rd]=R[rd]>>((h>>4)&31)
        elif (h>>9)==0x7a: R[rd]=u32(sx(R[rd],32)>>((h>>4)&31))
        else:
            s.log.append((a,'.half %04x (undef)'%h))
        s.pc=nxt
    def run(s):
        n=0
        while not s.stop and n<s.steps:
            if not (0<=s.pc<len(s.m.t)-1):
                s.log.append((s.pc,'PC out of text, stop')); break
            if s.trace:
                print('%06x %04x  r0=%08x r4=%08x r5=%08x r6=%08x sp=%08x fr=%d'%(
                    s.pc,s.th(s.pc),u32(s.R[0]),u32(s.R[4]),u32(s.R[5]),u32(s.R[6]),u32(s.R[15]),s.fr))
            s.step(); n+=1
        return n

def main():
    ap=sys.argv
    path=ap[1]; desc=int(ap[2],0); entry=int(ap[3],0)
    r={}; steps=200000; trace=False
    i=4
    while i<len(ap):
        if ap[i]=='--steps': steps=int(ap[i+1],0); i+=2
        elif ap[i]=='--trace': trace=True; i+=1
        elif ap[i].startswith('--r'): r[ap[i][2:]]=int(ap[i+1],0); i+=2
        elif ap[i]=='--sp': r['sp']=int(ap[i+1],0); i+=2
        else: i+=1
    m=ModAt(path,desc)
    print('module %s desc=%#x tbase=%#x tlen=%#x entry=%#x'%(os.path.basename(path),desc,m.tbase,len(m.t),entry))
    e=Emu(m,entry,r,steps,trace); n=e.run()
    print('steps=%d'%n)
    print('\n== run_engine (0009) command-table r0 values ==')
    for pc,r0 in e.cmdtables: print('  @%06x  r0=%08x'%(pc,r0))
    print('\n== engine-register writes (0x40000-0x4ffff), in order ==')
    for pc,ad,v in e.engine: print('  @%06x  [%05x] <- %08x'%(pc,ad,v))
    if e.log:
        print('\n== log/notes ==')
        for pc,msg in e.log[:40]: print('  @%06x  %s'%(pc,msg))

if __name__=='__main__': main()
