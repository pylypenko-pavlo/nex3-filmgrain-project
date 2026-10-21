#!/usr/bin/env python3
"""Static recursive-descent disassembly (control-flow walk, no execution) of one core image.
Entries: text+0x8 stub, segment heads ('b' at 06b0-style headers), and literal-pool values that point
at a push-prologue (str rX,[sp,#-4]! / str lr,[sp,#-4]!) or at a stub. Reports reached code and
opcodes undefined in ma1co's spec that lie on reached paths."""
import sys,os,re,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from mod import ModAt
import sadis
def walk(m,limit=None):
    t=m.t; H=struct.pack('<Q',0x0000080000000000); e=len(t)
    off=m.tbase%8   # VLIW header is 8-aligned in the file
    for o in range((8-off)%8,len(t)-7,8):
        if t[o:o+8]==H: e=o; break
    if limit: e=min(e,limit)
    # entries
    ent=set([8]) 
    for a in range(0,e-1,2):
        h=m.h(a)
        if h==0xb006: ent.add(a)                         # segment head 'b +0x10'
        if h>>12==5:
            tgt=(a&~3)+4+4*((h>>4)&0xff)
            if tgt+4<=len(t):
                v=struct.unpack_from('<I',t,tgt)[0]
                if 0<v<e and v%2==0 and (m.h(v)>>8==0x18 or m.h(v)==0x000a or m.h(v)>>4==0x00d):
                    ent.add(v)
    seen=set(); und=[]; data=set(); todo=list(ent)
    while todo:
        a=todo.pop()
        while 0<=a<e-1 and a not in seen:
            seen.add(a); h=m.h(a); op=h>>12
            if op==5: data.update(((a&~3)+4+4*((h>>4)&0xff),))
            if op==4: data.add((a&~1)+4+2*((h>>4)&0xff))
            s=sadis.dis1(m,a,set())
            if s.startswith('.half'): und.append((a,h)); break
            if (h>>4) in (0x00a,0x00b):                       # b/bl rd: resolve 'ldr rd,[pc]' feeding it
                rd=h&15
                for k in range(2,26,2):
                    p=m.h(a-k) if a-k>=0 else 0
                    if p>>12==5 and (p&15)==rd:
                        tg=(a-k&~3)+4+4*((p>>4)&0xff)
                        if tg+4<=len(m.t):
                            v=struct.unpack_from('<I',m.t,tg)[0]
                            if 0<v<e and v%2==0: todo.append(v)
                        break
            if h==0x0003: break                              # ret
            if (h>>4)==0x00a: break                          # b rd (indirect jump)
            if op==0xb: todo.append(a+4+2*sadis.sx(h&0xfff,12)); break
            if op in (0xc,0xd): todo.append(a+4+2*sadis.sx(h&0xfff,12))
            a+=2
    return seen,und,ent,data
if __name__=='__main__':
    m=ModAt(os.path.expanduser(sys.argv[1]),int(sys.argv[2],0))
    seen,und,ent,data=walk(m)
    print(f'entries {len(ent)} reached {len(seen)} halfwords, undefined-on-path {len(und)}')
    for a,h in und[:40]: print(f'  {a:#06x}: {h:04x}')
