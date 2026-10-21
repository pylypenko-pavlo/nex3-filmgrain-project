import sys,struct
from elfx import X
x=X(sys.argv[1]); T=set(int(a,16) for a in sys.argv[2:])
t=x.e.get_section_by_name('.text'); a=t['sh_addr']; o=x.v2o(a); d=x.d
for off in range(0,t['sh_size']-4,2):
    h=struct.unpack_from('<H',d,o+off)[0]; pc=a+off
    if (h&0xf800)==0xa000:
        tg=((pc+4)&~3)+(h&0xff)*4
        if tg in T: print('%x adr -> %x'%(pc,tg))
    # ADR.W T3: f20f 0xxx (add) / T2 f2af (sub)
    if h in (0xf20f,0xf2af):
        h2=struct.unpack_from('<H',d,o+off+2)[0]
        i=(h>>10)&1; imm3=(h2>>12)&7; imm8=h2&0xff
        # i is in h bit10 actually from first halfword encoding f20f -> i=0
        imm=(i<<11)|(imm3<<8)|imm8
        base=(pc+4)&~3; tg=base+imm if h==0xf20f else base-imm
        if tg in T: print('%x adr.w -> %x'%(pc,tg))
