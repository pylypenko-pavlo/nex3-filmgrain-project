import sys,struct,re
from elfx import X
x=X(sys.argv[1]); d=x.d
res=[]
for m in re.finditer(rb'\x00(\d{1,2}[A-Z][A-Za-z0-9_]+)\x00',d):
    nm=m.group(1).decode(); sv=x.o2v(m.start(1))
    j=d.find(struct.pack('<I',sv))
    while j>=0:
        if j%4==0:
            ti=x.o2v(j)-4; k=d.find(struct.pack('<I',ti))
            while k>=0:
                if k%4==0:
                    vt=x.o2v(k)+4; ents=[]
                    for i in range(200):
                        try: v=x.u32(vt+4*i)
                        except: break
                        if v&1 and 0x122780<v<0xef9cd0: ents.append(v-1)
                        elif v!=0 and not(v&1) and i>2: 
                            if v>0x2000000: break
                    for e in ents: res.append((e,nm))
                k=d.find(struct.pack('<I',ti),k+4)
        j=d.find(struct.pack('<I',sv),j+4)
res.sort()
import bisect
q=[int(a,16) for a in sys.argv[2:]]
for a in q:
    near=[r for r in res if abs(r[0]-a)<0x1200]
    print(hex(a), sorted(set(n for _,n in near)))
