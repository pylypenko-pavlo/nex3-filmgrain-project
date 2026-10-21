import sys,re
from trace import *
import io,contextlib
def calls(a0,a1,fn=0x307b0c,xblk=None):
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf): annotate(a0,a1,True)
    lines=buf.getvalue().splitlines()
    cur=[]; res=[]
    for k,l in enumerate(lines):
        m=re.search(r'; BK (\w+)\+0x(\w+) = 0x(\w+)',l)
        if m: cur.append((int(m.group(1),16),int(m.group(2),16),int(m.group(3),16)))
        elif re.search(r'ldr\w* r\d, \[(sp|r\d), #0x1[0-9a-f]{2}\]|ldrh r\d, \[r\d(, #0x\w+)?\]$',l) and 'BK' not in l:
            cur.append(('?',l.split(':')[0]))
        if ('bl #0x%x'%fn) in l:
            dest=''
            for l2 in lines[k+1:k+6]:
                if re.search(r'str\w* r0,',l2): dest=l2.split(': ')[1]; break
            res.append((l.split(':')[0],cur,dest)); cur=[]
        elif re.search(r': bl #',l): cur=[]
    return res
if __name__=='__main__':
    for addr,cur,dest in calls(int(sys.argv[1],16),int(sys.argv[2],16)):
        xs=[c for c in cur if c[0]!='?' and len(c)==3]
        X=[c for c in xs if (c[0],c[1]) in [(0x3000c,o) for o in range(6,0x1c,2)] or (c[0]==0x3010e and 8<=c[1]<=0x1c)]
        Y=[c for c in xs if c not in X]
        unk=[c for c in cur if c[0]=='?']
        Y.sort(key=lambda c:(c[0],c[1]))
        ys=' '.join('%x'%c[2] for c in Y)
        rng='%05x+%x..%x'%(Y[0][0],Y[0][1],Y[-1][1]) if Y else '-'
        print('%s  Y[%s] (%d) = %s %s  -> %s'%(addr,rng,len(Y),ys,(' PTR%d'%len(unk)) if unk else '',dest))
