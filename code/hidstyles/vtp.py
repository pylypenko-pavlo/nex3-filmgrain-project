import sys,struct
from elfx import X
def vts(x,name,n=130):
    d=x.d; i=d.find(b'\x00'+name.encode()+b'\x00')+1; sv=x.o2v(i); out=[]
    j=d.find(struct.pack('<I',sv))
    while j>=0:
        ti=x.o2v(j)-4; k=d.find(struct.pack('<I',ti))
        while k>=0:
            vt=x.o2v(k)+4
            if x.u32(vt-8)==0 or x.u32(vt-8)>=0xffffff00: out.append((vt,[x.u32(vt+4*m) for m in range(n)]))
            k=d.find(struct.pack('<I',ti),k+4)
        j=d.find(struct.pack('<I',sv),j+4)
    return out
xa=X(sys.argv[1]); xb=X(sys.argv[2])
for nm in sys.argv[3:]:
    A=vts(xa,nm); B=vts(xb,nm)
    for (va,ea),(vb,eb) in zip(A,B):
        pr=[]
        for p,q in zip(ea,eb):
            if p&1 and q&1: pr.append('%x:%x'%(p-1,q-1))
            elif (p==0)!=(q==0): pr.append('MISMATCH')
        print(nm,hex(va),hex(vb),' '.join(dict.fromkeys(pr)))
