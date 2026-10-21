#!/usr/bin/env python3
"""Recursive Thumb disassembler + call graph for av-cam.bin, to locate the
YC-buffer / JPEG-encode handling for a grain-injection hook.

Starts from known entry points (task entries from av-cam_3n.txt), follows BL/B
targets within the code range, records per-function literal-pool loads (to spot
pointers into imaging DRAM 0x84000000+, struct pointers, string-table refs).
"""
import sys,struct,os,re,collections
try: from capstone import *
except: os.system(sys.executable+' -m pip install -q capstone'); from capstone import *

AV=open(os.environ['NEX3N_AVCAM'],'rb').read()
BASE=0xc3441000
END=BASE+len(AV)
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB); md.detail=True

def rd(va,n):
    o=va-BASE
    return AV[o:o+n] if 0<=o<=len(AV)-n else b''
def word(va):
    o=va-BASE
    return struct.unpack_from('<I',AV,o)[0] if 0<=o<=len(AV)-4 else None

def disasm_fn(entry, maxins=4000):
    """linear+branch walk of one function from entry (thumb). returns (calls set, lits set, end)."""
    entry&=~1
    calls=set(); lits=set(); seen=set(); work=[entry]; lastaddr=entry
    while work:
        a=work.pop()
        if a in seen: continue
        code=rd(a,0x400)
        if not code: continue
        for ins in md.disasm(code,a):
            if ins.address in seen: break
            seen.add(ins.address); lastaddr=max(lastaddr,ins.address)
            m=ins.mnemonic; op=ins.op_str
            if m=='bl':
                t=(ins.operands[-1].imm & 0xffffffff) if ins.operands else None
                if t and BASE<=t<END: calls.add(t&~1)
            elif m in ('b','b.w'):
                t=(ins.operands[-1].imm & 0xffffffff) if ins.operands else None
                if t and BASE<=t<END and t&~1 not in seen: work.append(t&~1)
                break  # unconditional branch ends linear run
            elif m.startswith('b') and ins.operands:  # conditional
                t=ins.operands[-1].imm & 0xffffffff
                if t and BASE<=t<END and (t&~1) not in seen: work.append(t&~1)
            elif m in ('pop',) and 'pc' in op: break
            elif m in ('bx',) : break
            # literal loads
            if m.startswith('ldr') and '[pc' in op:
                mm=re.search(r'\[pc, #(-?\d+)\]',op)
                if mm:
                    t=((ins.address+4)&~3)+int(mm.group(1)); v=word(t)
                    if v is not None: lits.add(v)
            if m=='movw':
                pass
    return calls,lits,lastaddr

def main():
    # entry points
    entries={0xc344a790:'tsk46_jpeg',0xc3442f04:'tsk20_sdf',0xc3443284:'tsk21_sdf_jpegsort',
             0xc3443aa8:'tsk22_sdf_retouch',0xc3443c48:'tsk27_sdf_vsync'}
    graph={}; litmap={}
    q=list(entries); seenf=set()
    while q:
        f=q.pop()
        if f in seenf: continue
        seenf.add(f)
        calls,lits,end=disasm_fn(f)
        graph[f]=calls; litmap[f]=lits
        for c in calls:
            if c not in seenf: q.append(c)
        if len(seenf)>6000: break
    print(f"reached {len(seenf)} functions from {len(entries)} entries")
    # find functions whose literals point into imaging DRAM (0x84000000-0x90000000) = buffer handlers
    print("\nfunctions with literals into imaging DRAM (0x84000000-0x90000000):")
    hits=[]
    for f,lits in litmap.items():
        dram=[v for v in lits if 0x84000000<=v<0x90000000]
        if dram: hits.append((f,dram))
    for f,dram in hits[:20]:
        nm=entries.get(f,'')
        print(f"  {f:#x} {nm}  DRAM-lits: {[hex(v) for v in dram[:5]]}")
    # also: functions referencing the SA/engine MMIO or the enc_param struct area
    print(f"\n(total funcs with DRAM-lit refs: {len(hits)})")
    # save graph for further queries
    import pickle
    pickle.dump({'graph':graph,'litmap':{k:list(v) for k,v in litmap.items()},'entries':entries},
                open(os.environ.get('AVGRAPH_PKL','avgraph.pkl'),'wb'))
    print("saved avgraph.pkl")

if __name__=='__main__': main()
