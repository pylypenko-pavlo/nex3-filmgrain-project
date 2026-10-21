#!/usr/bin/env python3
"""Systematic SA-DSP VLIW microcode disassembler.
64-bit LE bundle: S0=bits[63:52] (12b header); slots S1=[51:39] S2=[38:26] S3=[25:13] S4=[12:0] (13b).
Slot = op[12:10].a[9:5].b[4:0].  op: 0 move(b=a), 1 pack/shift, 2 (undec xform), 3 read-stream(b=port a),
4 mul(b*=a), 5 store(datum a -> AGU chan b), 6 clamp(b=clamp a), 7 add(b+=a).  NOP=0x1f70fb87dc3ee1f7.

Usage: vliw_dis.py <module.bin> <start_off> <count>   (offsets are FILE offsets; bundles are 8 bytes)
       vliw_dis.py <module.bin> --auto                 (auto-detect & list coherent bundle regions)
Produces a full annotated listing with per-bundle slot decode + cross-bundle register dataflow.
"""
import sys,struct
NOP=0x1f70fb87dc3ee1f7
OP={0:'mov',1:'pk',2:'xf',3:'rd',4:'mul',5:'st',6:'clmp',7:'add'}
WRITES_B={0,1,2,3,4,6,7}   # ops whose slot WRITES register b (st writes memory, not a GPR)
READS_A ={0,1,2,4,6,7}     # ops that READ register a (rd reads a PORT, st reads datum a as a reg)

def slots(w):
    s0=(w>>52)&0xFFF; out=[]
    for sh in (39,26,13,0):
        s=(w>>sh)&0x1FFF; out.append(((s>>10)&7,(s>>5)&0x1F,s&0x1F))
    return s0,out

def sem(op,a,b):
    if op==0: return "r%d = r%d"%(b,a)
    if op==1: return "r%d = pk(r%d)"%(b,a)
    if op==2: return "r%d = xf(r%d)"%(b,a)
    if op==3: return "r%d = STREAM[port %d]"%(b,a)
    if op==4: return "r%d *= r%d"%(b,a)
    if op==5: return "STORE r%d -> chan %d"%(a,b)
    if op==6: return "r%d = clamp(r%d)"%(b,a)
    if op==7: return "r%d += r%d"%(b,a)

def disasm(f,start,count):
    lastdef={}   # reg -> (bundle_idx, slot) that last wrote it
    lines=[]
    for k in range(count):
        o=start+k*8
        if o+8>len(f): break
        w=struct.unpack_from('<Q',f,o)[0]
        s0,sl=slots(w)
        if w==NOP:
            lines.append("0x%04x  %016x  NOP"%(o,w)); continue
        parts=[]
        for si,(op,a,b) in enumerate(sl):
            tag=OP[op]
            note=""
            # dataflow: where did operand a come from?
            if op in READS_A and a in lastdef and op!=3:
                bi,bs=lastdef[a]; note=" ;a<-@0x%04x"%(start+bi*8)
            seg="S%d:%s %s%s"%(si+1,tag,sem(op,a,b),note)
            parts.append(seg)
        # update lastdef AFTER the bundle (intra-bundle: all slots see previous state)
        for si,(op,a,b) in enumerate(sl):
            if op in WRITES_B: lastdef[b]=(k,si)
        hot=""
        ops={op for op,_,_ in sl}
        if 5 in ops: hot=" <== STORE"
        elif 3 in ops: hot=" (stream)"
        lines.append("0x%04x  %016x  S0=%03x | %s%s"%(o,w,s0,"  |  ".join(parts),hot))
    return lines

def auto(f):
    N=len(f); i=0; regions=[]
    while i<N-8:
        w=struct.unpack_from('<Q',f,i)[0]
        if w!=NOP:
            # does it look like a plausible bundle? (not a scalar word) - heuristic: S0 small-ish & has a store/clamp/stream somewhere nearby
            j=i; good=0; tot=0
            while j<N-8:
                ww=struct.unpack_from('<Q',f,j)[0]
                s0,sl=slots(ww)
                ops={op for op,_,_ in sl}
                tot+=1
                if ww==NOP or (ops & {3,5,6}): good+=1
                else:
                    # break if a long non-bundle run
                    pass
                j+=8
                if j-i>0x600: break
            # crude: report runs starting at non-NOP with a store/clamp density
            i=j
        else: i+=8
    return regions

if __name__=='__main__':
    f=open(sys.argv[1],'rb').read()
    if sys.argv[2]=='--auto':
        print("auto-detect not wired; pass explicit start+count"); sys.exit()
    start=int(sys.argv[2],0); count=int(sys.argv[3],0)
    print("# VLIW disasm %s file 0x%x count %d"%(sys.argv[1].split('/')[-1],start,count))
    for l in disasm(f,start,count): print(l)
