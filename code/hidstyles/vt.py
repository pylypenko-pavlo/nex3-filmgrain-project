import sys,struct
from elfx import X
x=X(sys.argv[1]); name=sys.argv[2].encode()+b'\x00'
d=x.d
i=d.find(name)
while i>=0:
    if d[i-1:i]==b'\x00' or True:
        sv=x.o2v(i); print('str',hex(sv))
        pat=struct.pack('<I',sv)
        j=d.find(pat)
        while j>=0:
            ti=x.o2v(j)-4; print(' typeinfo',hex(ti))
            p2=struct.pack('<I',ti); k=d.find(p2)
            while k>=0:
                vt=x.o2v(k)+4
                ents=[x.u32(vt+4*n) for n in range(int(sys.argv[3]) if len(sys.argv)>3 else 24)]
                print('  vtable',hex(vt),[hex(e) for e in ents])
                k=d.find(p2,k+4)
            j=d.find(pat,j+4)
    i=d.find(name,i+1)
