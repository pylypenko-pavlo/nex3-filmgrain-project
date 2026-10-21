# annotate thumb disassembly: calls -> names, pc-rel literal loads, PIC add r,pc strings
import sys,struct
from elfx import X
x=X(sys.argv[1]); a0=int(sys.argv[2],16); a1=int(sys.argv[3],16)
lits={}
for ins in x.dis(a0,a1):
    note=''
    t=x.calltarget(ins)
    if t is not None: note=x.tname(t)
    if ins.mnemonic.startswith('ldr') and '[pc' in ins.op_str:
        try:
            imm=int(ins.op_str.split('#')[-1].rstrip(']'),16) if '#' in ins.op_str else 0
            la=((ins.address+4)&~3)+imm; v=x.u32(la); reg=ins.op_str.split(',')[0]
            lits[reg]=(ins.address,v); note='=0x%x'%v
        except Exception as ex: pass
    if ins.mnemonic=='add' and ins.op_str.endswith('pc'):
        reg=ins.op_str.split(',')[0]
        if reg in lits:
            v=(lits[reg][1]+ins.address+4)&0xffffffff
            sname=x.cstr(v) or x.syms.get(v) or x.absrel.get(v)
            note='-> 0x%x %s'%(v,sname or '')
    print('%x: %-8s %-30s %s'%(ins.address,ins.mnemonic,ins.op_str,note))
