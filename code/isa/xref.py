#!/usr/bin/env python3
"""Full-image BL cross-reference for av-cam.bin.
Linear Thumb sweep, collect every BL/BLX target -> {target: [callsites]}.
Cached to xref.pkl. Query: xref.py <target_va> lists callers.
"""
import sys,struct,os,pickle,collections
from capstone import *
AV=open(os.environ['NEX3N_AVCAM'],'rb').read()
BASE=0xc3441000; END=BASE+len(AV)
PKL=os.environ.get('XREF_PKL','xref.pkl')

def build():
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB); md.detail=False
    xref=collections.defaultdict(list)  # target -> [callsite]
    # linear sweep with resync: when disasm stalls, skip 2 bytes and continue.
    off=0; n=len(AV)
    while off < n-4:
        got=False
        for ins in md.disasm(AV[off:off+0x4000], BASE+off):
            got=True
            if ins.mnemonic in ('bl','blx'):
                op=ins.op_str
                if op.startswith('#'):
                    try: t=int(op[1:],0) & 0xffffffff
                    except: pass
                    else:
                        if BASE<=t<END: xref[t&~1].append(ins.address)
            off=ins.address - BASE + ins.size
        if not got: off+=2
    pickle.dump(dict(xref),open(PKL,'wb'))
    print(f"built xref: {len(xref)} targets, {sum(len(v) for v in xref.values())} callsites")
    return xref

def load():
    if not os.path.exists(PKL): return build()
    return pickle.load(open(PKL,'rb'))

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='build': build(); sys.exit()
    xref=load()
    if len(sys.argv)>1:
        t=int(sys.argv[1],16)&~1
        callers=xref.get(t,[])
        print(f"{t:#x}: {len(callers)} callers")
        for c in callers: print(f"  called from {c:#x} (off {c-BASE:#x})")
