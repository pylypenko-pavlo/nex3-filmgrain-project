# Minimal SA-DSP scalar assembler matching ma1co/sadis decode.
# 16-bit instructions. Returns list of (halfword) ints. Labels via two-pass.
import sys,struct
def R(x):
    x=x.strip()
    if x=='sp': return 15
    if x=='lr': return 14  # not a reg alias in ISA; avoid
    assert x[0]=='r', x
    return int(x[1:])
def asm(lines, org=0):
    # org = address of first instruction (for branch target calc)
    # pass1: addresses
    toks=[]
    for ln in lines:
        ln=ln.split(';')[0].strip()
        if not ln: continue
        toks.append(ln)
    labels={}; addr=org; prog=[]
    for t in toks:
        if t.endswith(':'):
            labels[t[:-1]]=addr; continue
        prog.append((addr,t)); addr+=2
    out=[]
    for (a,t) in prog:
        p=t.replace(',',' ').split()
        op=p[0]
        def imm(x):
            return int(x[1:],0) if x.startswith('#') else int(x,0)
        h=None
        if op=='nop': h=0x0000
        elif op=='ret': h=0x0003
        elif op=='wfi': h=0x0004
        elif op=='add' and p[1].startswith('r') and p[2].startswith('#') or (op=='add' and p[1]=='sp' and p[2].startswith('#')):
            d=R(p[1]); i=imm(p[2])&0xff; h=(0xa<<12)|(i<<4)|d
        elif op=='add':   # add d,s  (reg)
            d=R(p[1]); s=R(p[2]); h=(0x1e<<8)|(s<<4)|d
        elif op=='sub':
            d=R(p[1]); s=R(p[2]); h=(0x20<<8)|(s<<4)|d
        elif op=='mov' and p[2].startswith('#'):
            d=R(p[1]); i=imm(p[2])&0xff; h=(0x9<<12)|(i<<4)|d
        elif op=='mov':   # mov d,s
            d=R(p[1]); s=R(p[2]); h=(0x1b<<8)|(s<<4)|d
        elif op=='eor':
            d=R(p[1]); s=R(p[2]); h=(0x26<<8)|(s<<4)|d
        elif op=='and':
            d=R(p[1]); s=R(p[2]); h=(0x23<<8)|(s<<4)|d
        elif op=='orr':
            d=R(p[1]); s=R(p[2]); h=(0x24<<8)|(s<<4)|d
        elif op=='lsl' and p[2].startswith('#'):
            d=R(p[1]); n=imm(p[2])&31; h=(0x78<<9)|(n<<4)|d
        elif op=='lsr' and p[2].startswith('#'):
            d=R(p[1]); n=imm(p[2])&31; h=(0x79<<9)|(n<<4)|d
        elif op=='asr' and p[2].startswith('#'):
            d=R(p[1]); n=imm(p[2])&31; h=(0x7a<<9)|(n<<4)|d
        elif op=='lsl':
            d=R(p[1]); s=R(p[2]); h=(0x29<<8)|(s<<4)|d
        elif op=='lsr':
            d=R(p[1]); s=R(p[2]); h=(0x2a<<8)|(s<<4)|d
        elif op=='uxtb':
            d=R(p[1]); s=R(p[2]); h=(0x1c<<8)|(s<<4)|d
        elif op=='ldrb' and len(p)==4:   # ldrb d,[s,r0]
            d=R(p[1]); s=R(p[2].strip('[]')); assert p[3].strip('[]')=='r0'; h=(0x05<<8)|(s<<4)|d
        elif op=='ldrb' and len(p)==3:   # ldrb d,[s]
            d=R(p[1]); s=R(p[2].strip('[]')); h=(0x04<<8)|(s<<4)|d
        elif op=='strb' and len(p)==3:   # strb s,[d]
            s=R(p[1]); d=R(p[2].strip('[]')); h=(0x0d<<8)|(s<<4)|d
        elif op=='ldr' and len(p)==3:    # ldr d,[s]
            d=R(p[1]); s=R(p[2].strip('[]')); h=(0x0a<<8)|(s<<4)|d
        elif op=='str' and len(p)==4:    # str s,[d,#imm]  (op4=7 form, exactly as Probe S)
            s=R(p[1]); d=R(p[2].strip('[]')); off=imm(p[3].strip('[]'))//4; h=(0x7<<12)|((off&15)<<8)|(s<<4)|d
        elif op=='str' and len(p)==3:    # str s,[d]
            s=R(p[1]); d=R(p[2].strip('[]')); h=(0x15<<8)|(s<<4)|d
        elif op=='cmp.gtu':
            d=R(p[1]); s=R(p[2]); h=(0x31<<8)|(s<<4)|d
        elif op=='cmp.ges':
            d=R(p[1]); s=R(p[2]); h=(0x30<<8)|(s<<4)|d
        elif op=='cmp.gts':
            d=R(p[1]); s=R(p[2]); h=(0x32<<8)|(s<<4)|d
        elif op=='b':
            tgt=labels[p[1]] if p[1] in labels else int(p[1],0)
            disp=(tgt-(a+4))//2
            h=(0xb<<12)|(disp&0xfff)
        elif op=='bfs':
            tgt=labels[p[1]] if p[1] in labels else int(p[1],0)
            disp=(tgt-(a+4))//2
            h=(0xc<<12)|(disp&0xfff)
        elif op=='bfc':
            tgt=labels[p[1]] if p[1] in labels else int(p[1],0)
            disp=(tgt-(a+4))//2
            h=(0xd<<12)|(disp&0xfff)
        else:
            raise SystemExit(f'cannot assemble: {t!r}')
        out.append((a,h))
    return out,labels
if __name__=='__main__':
    src=open(sys.argv[1]).read().splitlines()
    org=int(sys.argv[2],0) if len(sys.argv)>2 else 0
    out,labels=asm(src,org)
    for a,h in out: print(f'{a:#07x}: {h:04x}')
    print('bytes:', sum(1 for _ in out)*2)
