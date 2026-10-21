import sys,struct
from elfx import X
x=X(sys.argv[1]); targets=set(int(a,16) for a in sys.argv[2:])
t=x.e.get_section_by_name('.text'); a=t['sh_addr']; o=x.v2o(a); d=x.d
for off in range(0,t['sh_size']-2,2):
    h=struct.unpack_from('<H',d,o+off)[0]
    if (h&0xff78)==0x4478:
        rd=h&7; pc=a+off
        for back in range(2,40,2):
            h2=struct.unpack_from('<H',d,o+off-back)[0]
            if (h2>>11)==0b01001 and ((h2>>8)&7)==rd:
                la=((pc-back+4)&~3)+(h2&0xff)*4; v=(x.u32(la)+pc+4)&0xffffffff
                if v in targets: print('%x -> %x'%(pc,v))
                break
    # GOT style: also check literal values directly equal to targets (absolute)
