import sys,struct,pickle,capstone,re,io
sys.path.insert(0,__import__('os').environ.get('PMCA_RE','Sony-PMCA-RE'))
from pmca.backup import BackupFile
D=open(__import__('os').environ['NEX3N_AVCAM'],'rb').read()
BASE=0xc3441000
A,B,R=pickle.load(open(__import__('os').environ['NEX3N_ADJMAP'],'rb'))
f=BackupFile(io.BytesIO(open(__import__('os').environ['NEX3N_BACKUP'],'rb').read()));P=dict(f.listProperties())
blocks=sorted((r,a,len(P[a].data)) for a,r in zip(A,R))
def ram2bk(v):
    for r,a,n in blocks:
        if r<=v<r+n: return (a,v-r)
    return None
def bkval(a,o,sz=2):
    d=P[a].data
    if o+sz>len(d): return None
    return int.from_bytes(d[o:o+sz],'little')
def cstr(off):
    m=re.match(rb"[\x20-\x7e]{4,100}",D[off:off+100]); return m.group(0).decode() if m else None
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB); md.detail=False
def sweep(a0,a1):
    a=a0; out=[]
    while a<a1:
        got=False
        for i in md.disasm(D[a:a1],a):
            out.append(i); a=i.address+i.size; got=True
        if not got or a<a1: a+=2
    return out
def annotate(a0,a1,show_all=False):
    regs={}; stk={}
    for i in sweep(a0,a1):
        txt="%x: %s %s"%(i.address,i.mnemonic,i.op_str); note=''
        m=re.match(r'(r\d+), \[pc, #(0x[0-9a-f]+|\d+)\]',i.op_str)
        if i.mnemonic.startswith('ldr') and m:
            L=((i.address+4)&~3)+int(m.group(2),0)
            if L+4<=len(D):
                v=struct.unpack_from('<I',D,L)[0]; regs[m.group(1)]=v
                bk=ram2bk(v)
                if bk: note='  ; =%08x -> BK %05x+0x%x'%(v,bk[0],bk[1])
                elif BASE<=v<BASE+len(D):
                    s=cstr(v-BASE); note='  ; =%08x %s'%(v,('"%s"'%s) if s else '')
                else: note='  ; =%x'%v
        elif i.mnemonic=='adr':
            m2=re.match(r'(r\d+), #(0x[0-9a-f]+|\d+)',i.op_str)
            L=((i.address+4)&~3)+int(m2.group(2),0); s=cstr(L); note='  ; "%s"'%s if s else ''
        elif i.mnemonic in('mov','movs') and re.match(r'(r\d+), (r\d+)$',i.op_str):
            a,b=re.match(r'(r\d+), (r\d+)$',i.op_str).groups()
            if b in regs: regs[a]=regs[b]
            else: regs.pop(a,None)
        elif i.mnemonic in('adds','subs','add','sub') and re.match(r'(r\d+), #(0x[0-9a-f]+|\d+)$',i.op_str):
            a,n=re.match(r'(r\d+), #(0x[0-9a-f]+|\d+)$',i.op_str).groups(); n=int(n,0)
            if a in regs:
                regs[a]+= n if i.mnemonic.startswith('add') else -n
                bk=ram2bk(regs[a]); note='  ; &BK %05x+0x%x'%bk if bk else ''
        elif re.match(r'(r\d+), \[sp(?:, #(0x[0-9a-f]+|\d+))?\]',i.op_str) and i.mnemonic in('str','ldr'):
            m=re.match(r'(r\d+), \[sp(?:, #(0x[0-9a-f]+|\d+))?\]',i.op_str); n=int(m.group(2) or '0',0)
            if i.mnemonic=='str':
                if m.group(1) in regs: stk[n]=regs[m.group(1)]
                else: stk.pop(n,None)
            else:
                if n in stk: regs[m.group(1)]=stk[n]; bk=ram2bk(stk[n]); note='  ; (stk) =%08x %s'%(stk[n],('-> BK %05x+0x%x'%bk) if bk else '')
                else: regs.pop(m.group(1),None)
        else:
            m=re.match(r'(r\d+), \[(r\d+)(?:, #(0x[0-9a-f]+|-?\d+))?\]',i.op_str)
            if m and m.group(2) in regs and i.mnemonic[:3] in('ldr','str'):
                v=regs[m.group(2)]+int(m.group(3) or '0',0); bk=ram2bk(v)
                if bk:
                    sz={'ldrh':2,'strh':2,'ldrb':1,'strb':1,'ldrsh':2,'ldrsb':1}.get(i.mnemonic,4)
                    note='  ; BK %05x+0x%x = 0x%x'%(bk[0],bk[1],bkval(bk[0],bk[1],sz) or 0)
            m=re.match(r'(r\d+), (r\d+), #(0x[0-9a-f]+|\d+)',i.op_str)
            if i.mnemonic.startswith('add') and m and m.group(2) in regs:
                v=regs[m.group(2)]+int(m.group(3),0); bk=ram2bk(v)
                if bk: note='  ; &BK %05x+0x%x'%bk
            # crude: invalidate dest
            m3=re.match(r'(r\d+),',i.op_str)
            if m3 and not note.startswith('  ; &') and not note.startswith('  ; (stk)') and m3.group(1) in regs and not i.mnemonic.startswith('str') and not i.mnemonic.startswith('cmp'): regs.pop(m3.group(1))
            if m and m.group(2) in regs and i.mnemonic.startswith('add'): regs[m.group(1)]=regs[m.group(2)]+int(m.group(3),0)
        if i.mnemonic in('bl','blx','push','pop') : 
            if i.mnemonic=='bl': regs={k:v for k,v in regs.items() if k in('r4','r5','r6','r7')}
        if show_all or note or i.mnemonic in('bl','push') : print(txt+note)
if __name__=='__main__':
    annotate(int(sys.argv[1],16),int(sys.argv[2],16),len(sys.argv)>3)
