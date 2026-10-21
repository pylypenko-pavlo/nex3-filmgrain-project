import sys
from elfx import X
x=X(sys.argv[1]); a0=int(sys.argv[2],16); a1=int(sys.argv[3],16)
for ins in x.dis(a0,a1):
    note=''
    if ins.mnemonic=='adr':
        tg=((ins.address+4)&~3)+int(ins.op_str.split('#')[1],16); note=repr(x.cstr(tg,2))
    t=x.calltarget(ins) if ins.mnemonic!='.hword' else None
    if t is not None: note=x.tname(t)
    if ins.mnemonic.startswith('ldr') and '[pc' in ins.op_str:
        imm=int(ins.op_str.split('#')[-1].rstrip(']'),16) if '#' in ins.op_str else 0
        note='=0x%x'%x.u32(((ins.address+4)&~3)+imm)
    print('%x: %-8s %-28s %s'%(ins.address,ins.mnemonic,ins.op_str,note))
