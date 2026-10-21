import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from saasm import asm
src=open(sys.argv[1]).read().splitlines()
org=int(sys.argv[2],0)
out,labels=asm(src,org)
buf=bytearray(org+len(out)*2+4)
for a,h in out:
    buf[a]=h&0xff; buf[a+1]=h>>8
open(sys.argv[3],'wb').write(buf)
print("labels:",{k:hex(v) for k,v in labels.items()})
print("routine bytes @",hex(org),"len",len(out)*2)
