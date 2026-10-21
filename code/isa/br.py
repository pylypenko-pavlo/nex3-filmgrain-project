from mod import *
import collections,sys
def pools(m):
    P=set()
    for a,r,t,v in lits(m):
        if t>a: P.add(t);P.add(t+2)
    return P
def sx(v,b): return v-(1<<b) if v>>(b-1)&1 else v
for n in sys.argv[1:]:
    m=Mod(n); P=pools(m)
    fs=set(v for a,r,t,v in lits(m) if v<len(m.t) and v%2==0 and v>0)
    for nib in [0xa,0xb,0xc,0xd,0xe,0xf]:
      for base in [0,2,4]:
        for sc in [2]:
          tot=bad=hitf=oob=0
          for a in range(0,len(m.t)-1,2):
            if a in P: continue
            h=m.h(a)
            if h>>12!=nib: continue
            t=a+base+sc*sx(h&0xfff,12); tot+=1
            if t<0 or t>=len(m.t): oob+=1
            elif t in P: bad+=1
            if t in fs: hitf+=1
          print(n,hex(nib),'base',base,'tot',tot,'oob',oob,'inpool',bad,'hitfunc',hitf)
