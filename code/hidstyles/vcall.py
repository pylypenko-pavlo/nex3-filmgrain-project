import sys,struct
from elfx import X
x=X(sys.argv[1])
t=x.e.get_section_by_name('.text'); a=t['sh_addr']; o=x.v2o(a)
d=x.d
# find 'adds rN,#0x80' (0x3080|N<<8) followed within 6 bytes by 'ldr rM,[rN,#0x20]' (0x6a00 | (8<<6)... ) ; ldr imm5: 0x6800 | imm5<<6 | rn<<3 | rt
for off in range(0,t['sh_size']-8,2):
    h=struct.unpack_from('<H',d,o+off)[0]
    if (h&0xf8ff)==0x3080:
        rn=(h>>8)&7
        for k in (2,4,6):
            h2=struct.unpack_from('<H',d,o+off+k)[0]
            if (h2&0xffc0)==(0x6800|(8<<6)) and ((h2>>3)&7)==rn:
                print(hex(a+off)); break
