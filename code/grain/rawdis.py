import sys,os,struct
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','isa'))
import sadis
class Raw:
    def __init__(s,path):
        s.t=open(path,'rb').read()
    def h(s,a): return s.t[a]|s.t[a+1]<<8
    def w32(s,a): return struct.unpack_from('<I',s.t,a)[0]
def run(path,s,e):
    m=Raw(path)
    # build literal-pool set from op4==5 loads within [s,e]
    pools=set()
    a=s
    while a<e-1:
        h=m.h(a)
        if h>>12==5:
            off=(h>>4)&0xff
            t=(a&~3)+4+4*off
            if s<=t<e: pools.add(t)
        a+=2
    a=s
    while a<e:
        if a in pools:
            print(f'{a:6x}:  .long {m.w32(a):#010x}'); a+=4; continue
        print(f'{a:6x}:  {m.h(a):04x}  {sadis.dis1(m,a,pools)}'); a+=2
if __name__=='__main__':
    path=sys.argv[1]; s=int(sys.argv[2],0); e=int(sys.argv[3],0)
    run(path,s,e)
