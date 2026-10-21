import sys,struct,re,os
d=open(sys.argv[1],'rb').read(); s=int(sys.argv[2],16); n=int(sys.argv[3])
names={}
sd=open(os.environ['NEX3N_STRINGS'],'rb').read()
for m in re.finditer(rb'(..)\x00\x1e([^\x00]{1,60})\x00',sd,re.S):
    i=int.from_bytes(m.group(1),'little'); names.setdefault(i,m.group(2).decode('utf8','replace'))
for k in range(n):
    w=struct.unpack_from('<8I',d,s+0x20*k)
    sid=w[1]&0xffff if (w[1]>>16)==0x200 else None
    print('%x'%(s+0x20*k),' '.join('%08x'%v for v in w), names.get(sid) if sid is not None else '')
