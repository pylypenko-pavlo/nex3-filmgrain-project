# helper: load ARM ELF .so, map PLT stubs to import names, disassemble ranges, find calls
import struct,bisect,re
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
import capstone
class X:
    def __init__(s,fn):
        s.fn=fn; s.d=open(fn,'rb').read(); s.e=ELFFile(open(fn,'rb'))
        s.segs=[(g['p_vaddr'],g['p_offset'],g['p_filesz']) for g in s.e.iter_segments() if g['p_type']=='PT_LOAD']
        s.syms={}; s.funcs=[]
        ds=s.e.get_section_by_name('.dynsym')
        s.dynsym=list(ds.iter_symbols())
        for sy in s.dynsym:
            if sy['st_value'] and sy['st_shndx']!='SHN_UNDEF':
                s.syms[sy['st_value']&~1]=sy.name
                if sy['st_info']['type']=='STT_FUNC': s.funcs.append((sy['st_value']&~1,sy['st_size'],sy.name))
        s.funcs.sort(); s.fa=[f[0] for f in s.funcs]
        # plt
        s.plt={}
        rp=s.e.get_section_by_name('.rel.plt'); plt=s.e.get_section_by_name('.plt')
        got2name={}
        for r in rp.iter_relocations():
            got2name[r['r_offset']]=s.dynsym[r['r_info_sym']].name
        pa,ps=plt['sh_addr'],plt['sh_size']
        # ARM plt stubs: add ip,pc,#..; add ip,ip,#..; ldr pc,[ip,#..]!
        def rot(x): imm=x&0xff; r=((x>>8)&0xf)*2; return ((imm>>r)|(imm<<(32-r)))&0xffffffff
        a=pa+16
        while a<pa+ps-8:
            w0=struct.unpack_from('<I',s.d,s.v2o(a))[0]
            th=False
            if w0==0x46c04778: th=True; arm=a+4
            else: arm=a
            w=[struct.unpack_from('<I',s.d,s.v2o(arm)+4*i)[0] for i in range(3)]
            if (w[0]&0xfffff000)==0xe28fc000:
                got=arm+8+rot(w[0])+rot(w[1])+(w[2]&0xfff)
                nm=got2name.get(got,'?%x'%got)
                s.plt[arm]=nm
                if th: s.plt[a]=nm
                a=arm+12
            else: a+=4
        # data relocs (R_ARM_ABS32 / GLOB_DAT) for pointers in data
        s.absrel={}
        rd=s.e.get_section_by_name('.rel.dyn')
        for r in rd.iter_relocations():
            if r['r_info_sym']: s.absrel[r['r_offset']]=s.dynsym[r['r_info_sym']].name
        s.md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB); s.md.detail=False
    def v2o(s,v):
        for va,o,sz in s.segs:
            if va<=v<va+sz: return v-va+o
    def o2v(s,off):
        for va,o,sz in s.segs:
            if o<=off<o+sz: return off-o+va
    def u32(s,v): return struct.unpack_from('<I',s.d,s.v2o(v))[0]
    def fname(s,a):
        i=bisect.bisect_right(s.fa,a)-1
        if i>=0 and a< s.funcs[i][0]+max(s.funcs[i][1],2): return s.funcs[i][2]
        return None
    def cstr(s,v,mn=3):
        o=s.v2o(v)
        if o is None: return None
        m=re.match(rb'[\x20-\x7e]{%d,200}\x00'%mn,s.d[o:o+201])
        return m.group(0)[:-1].decode() if m else None
    def dis(s,a0,a1):
        out=[]; a=a0
        while a<a1:
            o=s.v2o(a); got=False
            for ins in s.md.disasm(s.d[o:o+(a1-a)],a):
                out.append(ins); a=ins.address+ins.size; got=True
            if a<a1:
                class B: pass
                b=B(); b.address=a; b.size=2; b.mnemonic='.hword'; b.op_str='0x%04x'%int.from_bytes(s.d[s.v2o(a):s.v2o(a)+2],'little'); out.append(b); a+=2
        return out
    def calltarget(s,ins):
        if ins.mnemonic in('bl','blx'):
            try: t=int(ins.op_str.lstrip('#'),16)
            except: return None
            return t
    def tname(s,t):
        if t is None: return None
        if t in s.plt: return s.plt[t]
        return s.syms.get(t) or s.fname(t) or hex(t)
