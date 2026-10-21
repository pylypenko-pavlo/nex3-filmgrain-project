import os,sys,struct
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','isa'))
import sadis
class Raw:
    def __init__(s,path): s.t=open(path,'rb').read()
    def h(s,a): return s.t[a]|s.t[a+1]<<8
    def w32(s,a): return struct.unpack_from('<I',s.t,a)[0]
m=Raw(sys.argv[1]); s=int(sys.argv[2],0); e=int(sys.argv[3],0)
# find interesting markers
a=s
while a<e-1:
    h=m.h(a)
    tag=None
    if h==0x00df: tag="PROLOGUE str lr,[sp,#-4]!"
    elif h==0x0003: tag="RET"
    elif h==0x0004: tag="wfi"
    elif (h>>4)==0x00b: tag=f"bl r{h&15}"
    elif h>>12==0xb:
        disp=h&0xfff; disp = disp-0x1000 if disp>>11 else disp
        tag=f"b {a+4+2*disp:#x}"
    if tag: print(f"{a:6x}: {h:04x}  {tag}")
    a+=2
