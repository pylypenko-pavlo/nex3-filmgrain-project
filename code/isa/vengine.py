#!/usr/bin/env python3
"""Symbolic VLIW simulator for the Sony SA-DSP engine, to probe op3 semantics.

Approach: we know the Soft Focus VLIW program computes a convolution
(weighted sum of pixels). We run the bundle program symbolically with a
hypothesised op3->operation mapping and measure whether the result looks
like a convolution (a sum of products of register leaves). The mapping that
best produces that structure is evidence for the op semantics.

Bundle format (section 16/23): 12-bit S0 + 4x13-bit slots; slot = op3.a5.b5;
dst = b, src = a (resolved in 23.1). Idle slot = (op0,a15,b23); fill = (op7,a31,b31).

This does NOT need pixel values: it works on the dataflow structure. It also
cannot by itself fix the full execution model (how inputs map to registers);
it narrows which op is multiply vs add vs move from the expression shape.
"""
import sys,os,struct,itertools
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
NOP=0x1f70fb87dc3ee1f7; HDR=0x0000080000000000
PARTS=[(51,39),(38,26),(25,13),(12,0)]
IDLE={(0,15,23),(7,31,31)}

def load_program(path, min_active=40):
    b=open(path,'rb').read(); q=list(struct.unpack_from('<%dQ'%(len(b)//8),b,0))
    i=0;n=len(q)
    while i<n:
        if q[i]==HDR:
            j=i+1;bs=[]
            while j<n and q[j]!=0: bs.append(q[j]);j+=1
            if sum(1 for w in bs if w!=NOP)>=min_active: return i*8,bs
            i=j
        else:i+=1
    return None,None

def decode(w):
    sl=[(w>>lo)&((1<<(hi-lo+1))-1) for hi,lo in PARTS]
    return w>>52,[(s>>10,(s>>5)&31,s&31) for s in sl]

# ---- symbolic expressions: nested tuples, with size/structure metrics ----
def leaf(r): return ('L',r)
def mk(op,a,b):
    return (op,a,b)

def ops_count(e,acc=None):
    if acc is None: acc={'MUL':0,'ADD':0,'SUB':0,'MOV':0,'OTHER':0,'depth':0,'leaves':set()}
    def rec(x,d):
        acc['depth']=max(acc['depth'],d)
        if x[0]=='L': acc['leaves'].add(x[1]); return
        if x[0] in acc: acc[x[0]]+=1
        else: acc['OTHER']+=1
        for c in x[1:]:
            if isinstance(c,tuple): rec(c,d+1)
    rec(e,0); return acc

def conv_score(e):
    """higher = more convolution-like (sum of products): many MULs feeding ADDs, few others."""
    a=ops_count(e)
    if a['MUL']==0 or a['ADD']==0: return -1
    # ideal: products summed. penalize OTHER/SUB/MOV noise and crazy depth
    return a['MUL']+a['ADD'] - 3*a['OTHER'] - a['SUB'] - 0.1*a['depth']

class Sim:
    def __init__(s,sem):
        # sem: dict op3(int)->'MUL'|'ADD'|'SUB'|'MOV'|'NOP'
        s.sem=sem; s.R=[leaf(i) for i in range(32)]; s.steps=0
    def run(s,bundles,limit=400):
        for w in bundles:
            if w==NOP: continue
            s0,slots=decode(w)
            # apply the 4 slots; dst=b, src=a (parallel read then write)
            reads=[(op,a,b) for (op,a,b) in slots]
            newvals=[]
            for (op,a,b) in reads:
                if (op,a,b) in IDLE: continue
                kind=s.sem.get(op,'OTHER')
                dst=b; src=a
                if kind=='NOP': continue
                if kind=='MOV': val=s.R[src]
                elif kind in ('MUL','ADD','SUB'): val=mk(kind,s.R[dst],s.R[src])
                else: val=mk('OTHER',s.R[dst],s.R[src])
                newvals.append((dst,val))
            for dst,val in newvals: s.R[dst]=val
            s.steps+=1
            if s.steps>=limit: break
        return s.R

def main():
    path=sys.argv[1] if len(sys.argv)>1 else os.path.expanduser('~/nex3n-dump/sonygen/out3n/nflasha8_unpacked_unpacked/sabin/sa_sftfcs.bin')
    off,bs=load_program(path)
    if bs is None: print('no program'); return
    # limit to the active compute core (first N active bundles)
    active=[w for w in bs if w!=NOP][:60]
    print(f'program @ {off:#x}, running first {len(active)} active bundles')
    # op0=idle/MOV, op7=fill/accumulate(ADD?), op3=r24 load(MOV?). search op1,2,4,5,6 roles.
    kinds=['MUL','ADD','MOV']
    best=[]
    base={0:'MOV',3:'MOV',7:'ADD'}  # hypotheses for the role ops
    for combo in itertools.product(kinds,repeat=5):
        sem=dict(base);
        for op,k in zip([1,2,4,5,6],combo): sem[op]=k
        sim=Sim(sem); R=sim.run(active)
        # score the most-written accumulator regs (1,14,5,31,19) outputs
        sc=max(conv_score(R[r]) for r in (1,14,5,31,19,30))
        best.append((sc,sem))
    best.sort(key=lambda x:-x[0])
    print('\ntop op-semantic hypotheses by convolution-likeness of output regs:')
    for sc,sem in best[:6]:
        row={k:sem[k] for k in sorted(sem)}
        print(f'  score {sc:6.1f}  {row}')
    # detail the best
    sc,sem=best[0]
    sim=Sim(sem); R=sim.run(active)
    print('\nbest hypothesis output structure (regs 1/14/5/31/19):')
    for r in (1,14,5,31,19):
        a=ops_count(R[r]); print(f'  r{r}: MUL={a["MUL"]} ADD={a["ADD"]} MOV={a["MOV"]} OTHER={a["OTHER"]} depth={a["depth"]} leaves={len(a["leaves"])}')

if __name__=='__main__': main()
