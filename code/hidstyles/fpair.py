import sys
from elfx import X
from fdiff import starts,body
import difflib
xa=X(sys.argv[1]); xb=X(sys.argv[2])
sa,ea=starts(xa); sb,eb=starts(xb)
pairs=[(int(a,16),int(b,16)) for a,b in (p.split(':') for p in sys.argv[3:])]
seen=set(); q=list(pairs)
while q:
    a,b=q.pop(0)
    if (a,b) in seen: continue
    seen.add((a,b))
    la,ca,_=body(xa,sa,ea,a); lb,cb,_=body(xb,sb,eb,b)
    ta=[l[1] for l in la]; tb=[l[1] for l in lb]
    if ta!=tb:
        print('### DIFF fn 3N %x (%d ins) vs N6 %x (%d ins)'%(a,len(ta),b,len(tb)))
        for line in difflib.unified_diff(ta,tb,lineterm='',n=2): print('   ',line)
    else: print('same fn 3N %x N6 %x (%d ins)'%(a,b,len(ta)))
    if len(ca)==len(cb):
        for c1,c2 in zip(ca,cb):
            if len(seen)<400: q.append((c1,c2))
    else: print('   call count mismatch',len(ca),len(cb))
