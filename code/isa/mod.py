import struct,os
D=os.environ.get('NEX3N_SABIN','sabin')
def images(b):
    out=[]; o=0x30
    while o+16<=0x100:
        off=struct.unpack_from('<I',b,o)[0]; name=b[o+4:o+16].rstrip(b'\0')
        if off and off<len(b) and b[off]==0x3d and b[off+3]==0xb0: out.append((off,name.decode('latin1')))
        o+=16
    return out
class Mod:
    def __init__(s,n,d=D,img=0):
        n=n.split("/")[-1]
        b=open(f'{d}/{n}','rb').read(); s.name=n; s.raw=b
        ims=images(b); s.images=ims
        s.desc=ims[img][0] if ims else 0x100
        w=struct.unpack_from('<16I',b,s.desc); s.w=w
        s.tbase=s.desc+w[4]; s.tend=s.desc+w[5]
        s.t=b[s.tbase:s.tend]
    def h(s,a): return s.t[a]|s.t[a+1]<<8
    def w32(s,a): return struct.unpack_from('<I',s.t,a)[0]
def lits(m):
    out=[]
    for a in range(0,len(m.t)-1,2):
        h=m.h(a)
        if h>>12==5:
            off=(h>>4)&0xff
            t=(a&~3)+4+4*off
            if t+4<=len(m.t): out.append((a,h&0xf,t,m.w32(t)))
    return out

class ModAt(Mod):
    """module image whose descriptor sits at file offset `desc` (any core image)"""
    def __init__(s,path,desc):
        b=open(path,'rb').read(); s.name=path; s.raw=b; s.desc=desc
        w=struct.unpack_from('<16I',b,desc); s.w=w
        # v2: w[4]=text base; v4/v5: w[5] is text base (w[4] looks like a size)
        base=w[4] if b[4]<=2 else w[5]
        s.tbase=desc+base
        end=w[5] if b[4]<=2 else w[6]
        s.tend=min(len(b),desc+end) if end>base else len(b)
        s.t=b[s.tbase:s.tend]
