import os,struct,sys
def scan(d):
    hits=[]
    n=len(d)
    for a in range(0,n-4,4):
        w=struct.unpack_from("<I",d,a)[0]
        if (w&0x0e000fff)==0x020008bd and (w>>28)==0xe: hits.append(("arm-imm",a,w))
        if (w&0x0ff00fff)==0x034000bd and (w>>28)==0xe: hits.append(("arm-movt",a,w))
    for a in range(0,n-4,2):
        h1,h2=struct.unpack_from("<HH",d,a)
        if (h1>>11)==0b11110 and (h1&0x0200)==0 and (h1&0x0400) and (h2&0x8000)==0 and (h2&0x70ff)==0x003d and (h1&0xf)!=0xf or ((h1>>11)==0b11110 and (h1&0x0200)==0 and (h1&0x0400) and (h2&0x8000)==0 and (h2&0x70ff)==0x003d): hits.append(("t2-imm",a,(h1<<16)|h2))
        if h1==0xf2c0 and (h2&0xf0ff)==0x00bd: hits.append(("t2-movt",a,(h1<<16)|h2))
    return hits
roots=sys.argv[1:]
for r in roots:
  for dp,dn,fn in os.walk(r):
    for f in fn:
        p=os.path.join(dp,f)
        if os.path.islink(p) or not os.path.isfile(p): continue
        d=open(p,"rb").read()
        if not (d[:4]==b"\x7fELF" or p.endswith(".ko") or "vmlinux" in p): continue
        h=scan(d)
        if h: print(p.split("out3n/")[-1],len(h),[(k,hex(a)) for k,a,w in h[:6]])
