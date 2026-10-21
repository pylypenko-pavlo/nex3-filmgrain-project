# av-cam xref helpers (Thumb-2). base 0xc3441000
import struct,re,bisect,capstone,pickle,os
F=os.environ['NEX3N_AVCAM']
B=0xc3441000
d=open(F,"rb").read(); N=len(d)
def u32(o): return struct.unpack_from("<I",d,o)[0]
def u16(o): return struct.unpack_from("<H",d,o)[0]
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB); md.detail=False
def dis(o0,o1):
    out=[]
    for i in md.disasm(d[o0:o1],B+o0): out.append(i)
    return out
def pdis(o0,o1,ann=True):
    for i in md.disasm(d[o0:o1],B+o0):
        s="%07x %08x: %-8s %s"%(i.address-B,i.address,i.mnemonic,i.op_str)
        if ann and i.mnemonic.startswith("ldr") and "[pc" in i.op_str:
            m=re.search(r"#(-?0x[0-9a-f]+|-?\d+)\]",i.op_str); imm=int(m.group(1),0) if m else 0
            pa=((i.address+4)&~3)+imm-B
            if 0<=pa<N-4:
                v=u32(pa); s+="   ; =%08x %s"%(v,cs(v))
        if i.mnemonic in("bl","blx","b.w") :
            try: t=int(i.op_str.strip("#"),0); s+="   ; "+fn(t-B)
            except: pass
        print(s)
def cs(v):
    o=v-B
    if 0<=o<N:
        m=re.match(rb"[\x20-\x7e\n]{3,100}\x00",d[o:o+101])
        if m: return repr(m.group(0)[:-1].decode())
    return ""
CACHE=os.path.join(os.path.dirname(os.path.abspath(__file__)),"litref.pkl")
def build():
    pool={}  # pool offset -> list of code offsets (ldr literal)
    for a in range(0,N-4,2):
        h=u16(a)
        if (h>>11)==0b01001:
            p=((a+4)&~3)+(h&0xff)*4
            pool.setdefault(p,[]).append(a)
        elif h==0xf8df or (h&0xff7f)==0xf85f:
            h2=u16(a+2); imm=h2&0xfff; up=1 if h==0xf8df else (1 if (h&0x80) else -1)
            p=((a+4)&~3)+up*imm
            pool.setdefault(p,[]).append(a)
    bl={}  # target -> callers (T32 BL/BLX)
    for a in range(0,N-4,2):
        h1=u16(a); h2=u16(a+2)
        if (h1>>11)==0b11110 and (h2>>14)==0b11 and (h2&0x1000 or True):
            if (h2>>12)&1 or ((h2>>12)&5)==4:
                S=(h1>>10)&1; imm10=h1&0x3ff; J1=(h2>>13)&1; J2=(h2>>11)&1; imm11=h2&0x7ff
                I1=1-(J1^S); I2=1-(J2^S)
                off=(S<<24)|(I1<<23)|(I2<<22)|(imm10<<12)|(imm11<<1)
                if S: off-=1<<25
                t=a+4+off
                if (h2>>12)&1==0: t&=~3
                if 0<=t<N: bl.setdefault(t,[]).append(a)
    pickle.dump((pool,bl),open(CACHE,"wb"))
    return pool,bl
def load():
    if os.path.exists(CACHE): return pickle.load(open(CACHE,"rb"))
    return build()
POOL,BL=load()
def strrefs(s):
    r=[]
    for m in re.finditer(re.escape(s.encode()),d):
        o=m.start()
        # back to string start
        st=o
        while st>0 and 0x20<=d[st-1]<0x7f: st-=1
        v=B+st; pat=struct.pack("<I",v); i=-1
        while True:
            i=d.find(pat,i+1)
            if i<0: break
            if i%4==0: r.append((st,i,POOL.get(i,[])))
    return r
def fstart(o):
    # search back for push {...,lr}
    a=o&~1
    while a>0 and o-a<0x4000:
        h=u16(a)
        if (h&0xff00)==0xb500: return a
        if h==0xe92d and (u16(a+2)&0x4000): return a
        a-=2
    return None
def fn(o):
    s=fstart(o) if o>=0 else None
    return "fn_%x+%x"%(s,o-s) if s is not None else "?%x"%o
def refs_to_word(v):
    pat=struct.pack("<I",v); i=-1; r=[]
    while True:
        i=d.find(pat,i+1)
        if i<0: return r
        if i%4==0: r.append((i,POOL.get(i,[])))
def adrrefs(t):
    res=[]
    for a in range(max(0,t-0x100000)&~1, min(N-4,t+0x1000),2):
        h=u16(a)
        if (h>>11)==0b10100 and ((a+4)&~3)+(h&0xff)*4==t: res.append(("T16adr",a))
        if (h&0xfbff)==0xf20f or (h&0xfbff)==0xf2af:
            h2=u16(a+2)
            imm=((h>>10)&1)<<11 | ((h2>>12)&7)<<8 | (h2&0xff)
            if (h&0xfbff)==0xf2af: imm=-imm
            if ((a+4)&~3)+imm==t: res.append(("T32adr",a))
    return res
def pretty(f,span=0x600):
    names=set()
    for x in dis(f,f+span):
        if x.mnemonic.startswith("ldr") and "[pc" in x.op_str:
            m=re.search(r"#(-?0x[0-9a-f]+|-?\d+)\]",x.op_str); imm=int(m.group(1),0) if m else 0
            pa=((x.address+4)&~3)+imm-B
            if 0<=pa<N-4:
                s=cs(u32(pa))
                if "::" in s and "(" in s: names.add(s)
        if x.mnemonic=="pop" and "pc" in x.op_str and names: break
    return names
