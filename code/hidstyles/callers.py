import sys,re,struct
from elfx import X
x=X(sys.argv[1]); pat=re.compile(sys.argv[2])
t=x.e.get_section_by_name('.text'); a=t['sh_addr']; end=a+t['sh_size']
# brute: decode every halfword position for 32-bit BL/BLX
d=x.d; o0=x.v2o(a)
for off in range(0,end-a-4,2):
    h1,h2=struct.unpack_from('<HH',d,o0+off)
    if (h1&0xf800)==0xf000 and (h2&0xc000)==0xc000:
        S=(h1>>10)&1; imm10=h1&0x3ff; J1=(h2>>13)&1; J2=(h2>>11)&1; imm11=h2&0x7ff
        I1=1-(J1^S); I2=1-(J2^S)
        imm=(S<<24)|(I1<<23)|(I2<<22)|(imm10<<12)|(imm11<<1)
        if S: imm-=1<<25
        pc=a+off+4
        if h2&0x1000: tg=pc+imm
        else: tg=(pc&~3)+imm
        n=x.tname(tg)
        if n and pat.search(n): print('%x %s'%(a+off,n))
