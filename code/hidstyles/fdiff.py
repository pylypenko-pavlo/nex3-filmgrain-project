import sys,struct,difflib,re
from elfx import X
def starts(x):
    t=x.e.get_section_by_name('.text'); a=t['sh_addr']; o=x.v2o(a); d=x.d; S=set()
    for off in range(0,t['sh_size']-4,2):
        h1,h2=struct.unpack_from('<HH',d,o+off)
        if (h1&0xf800)==0xf000 and (h2&0xd000)==0xd000:
            Sb=(h1>>10)&1; imm10=h1&0x3ff; J1=(h2>>13)&1; J2=(h2>>11)&1; imm11=h2&0x7ff
            I1=1-(J1^Sb); I2=1-(J2^Sb); imm=(Sb<<24)|(I1<<23)|(I2<<22)|(imm10<<12)|(imm11<<1)
            if Sb: imm-=1<<25
            tg=a+off+4+imm
            if a<=tg<a+t['sh_size']: S.add(tg)
    # pointers in data to thumb code
    for sec in ('.data.rel.ro','.data'):
        s=x.e.get_section_by_name(sec)
        if not s: continue
        for i in range(0,s['sh_size'],4):
            v=struct.unpack_from('<I',d,s['sh_offset']+i)[0]
            if v&1 and a<=v-1<a+t['sh_size']: S.add(v-1)
    for f in x.funcs: S.add(f[0])
    return sorted(S),a+t['sh_size']
def body(x,st,end,a):
    import bisect
    i=bisect.bisect_right(st,a); b=st[i] if i<len(st) else end
    lines=[]; calls=[]
    lits={}
    for ins in x.dis(a,min(b,a+0x2000)):
        op=ins.op_str
        if ins.mnemonic=='.hword': op='?'
        t=x.calltarget(ins) if ins.mnemonic!='.hword' else None
        if t is not None:
            n=x.tname(t)
            if n.startswith('0x'): calls.append(t); op='LOCAL'
            else: op=n
        elif ins.mnemonic.startswith('b') and op.startswith('#0x'): op='L'
        if ins.mnemonic.startswith('ldr') and '[pc' in op:
            imm=int(op.split('#')[-1].rstrip(']'),16) if '#' in op else 0
            v=x.u32(((ins.address+4)&~3)+imm); reg=op.split(',')[0]; lits[reg]=v
            op=reg+',=%s'%('%x'%v if (v<0x10000 and False) else ('%08x'%v if 0x01000000<=v<0x03000000 or v<0x400 else 'PIC'))
        if ins.mnemonic=='add' and op.endswith('pc') and op.split(',')[0] in lits:
            v=(lits[op.split(',')[0]]+ins.address+4)&0xffffffff
            op+=' -> '+(x.cstr(v) or x.absrel.get(v) or 'data')
        lines.append(('%x'%ins.address, ins.mnemonic+' '+op))
    return lines,calls,b
