# normalized disassembly: replace addresses with names/relative, for diffing
import sys,re
from elfx import X
x=X(sys.argv[1]); a0=int(sys.argv[2],16); a1=int(sys.argv[3],16)
lits={}
for ins in x.dis(a0,a1):
    op=ins.op_str; note=''
    t=x.calltarget(ins)
    if t is not None:
        n=x.tname(t); op = n if not n.startswith('0x') else 'L%+x'%(t-a0)
    elif ins.mnemonic.startswith('b') and op.startswith('#0x'):
        op='L%+x'%(int(op[1:],16)-a0)
    if ins.mnemonic.startswith('ldr') and '[pc' in op:
        imm=int(op.split('#')[-1].rstrip(']'),16) if '#' in op else 0
        la=((ins.address+4)&~3)+imm; v=x.u32(la); reg=op.split(',')[0]; lits[reg]=v
        op=reg+', =LIT'; note='%x'%v if v<0x10000000 and (v>>16) not in (0,1,2,3,4,5,6) else 'lit%08x'%v
        if (v>>24) in (1,2) : note='%08x'%v
        else: note=''
        if 0x01000000<=v<0x03000000: note='%08x'%v
        elif v<0x1000: note='%x'%v
    if ins.mnemonic=='add' and op.endswith('pc'):
        reg=op.split(',')[0]
        if reg in lits:
            v=(lits[reg]+ins.address+4)&0xffffffff
            s=x.cstr(v) or x.absrel.get(v)
            note='-> %s'%(s or 'data')
    print('%-6s %s %s'%(ins.mnemonic,op,note))
