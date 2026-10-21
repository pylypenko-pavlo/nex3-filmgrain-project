# NEX3N_DUMP: root of the firmware dump tree (default ./nex3n-dump)
import os,sys,struct,hashlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from saasm import asm
from gen_routine import routine_src

DUMP=os.environ.get('NEX3N_DUMP','nex3n-dump')
STOCK=os.path.join(DUMP,'safeboot/out3n/nflasha8_unpacked_unpacked/sabin/sa_yknr.bin')
CORES=[0xac50,0xb240,0xb830,0xbe20,0xc410]
HOOK_OFF=0x2fa        # chunk+0x2fa : the 'add sp,#0x50' epilogue instr
ROUT_OFF=0x13c        # chunk+0x13c : routine placement (0xad8c..0xadd6 in core0)
BACK=0xaf4c           # core0 chunk+0x2fc return point

def sum32(buf):
    # sum of all u32 words except the final trailer word
    n=(len(buf)//4)-1
    s=0
    for i in range(n):
        s=(s+struct.unpack_from('<I',buf,i*4)[0])&0xffffffff
    return s

def routine_bytes(N,mask,org):
    out,labels=asm(routine_src(N,mask).splitlines(),org)
    bs=bytearray()
    for a,h in out: bs+=struct.pack('<H',h)
    return bytes(bs),labels

def hook_bytes(core_hook_addr, core_rout_addr):
    # 'b routine' at the hook site
    disp=(core_rout_addr-(core_hook_addr+4))//2
    h=(0xb<<12)|(disp&0xfff)
    return struct.pack('<H',h)

def build(out_path, per_core):
    # per_core: dict core_index -> (N,mask) ; cores not listed stay stock
    buf=bytearray(open(STOCK,'rb').read())
    changes=[]
    for ci,base in enumerate(CORES):
        if ci not in per_core: continue
        N,mask=per_core[ci]
        rout_file=base+ROUT_OFF
        hook_file=base+HOOK_OFF
        # routine bytes are position-independent; assemble at core0 placement so BACK resolves,
        # the SAME bytes work at every core (stride 0x5f0 keeps all displacements valid).
        rb,labels=routine_bytes(N,mask, CORES[0]+ROUT_OFF)
        buf[rout_file:rout_file+len(rb)]=rb
        changes.append((rout_file,rout_file+len(rb)))
        hb=hook_bytes(CORES[0]+HOOK_OFF, CORES[0]+ROUT_OFF)
        buf[hook_file:hook_file+2]=hb
        changes.append((hook_file,hook_file+2))
    # recompute sum32 trailer (last u32)
    s=sum32(buf)
    struct.pack_into('<I',buf,len(buf)-4,s)
    open(out_path,'wb').write(buf)
    md5=hashlib.md5(buf).hexdigest()
    return md5,s,changes,len(rb)

if __name__=='__main__':
    # sanity: verify sum32 reproduces stock trailer
    stock=open(STOCK,'rb').read()
    calc=sum32(stock); stored=struct.unpack_from('<I',stock,len(stock)-4)[0]
    print(f'stock sum32 calc={calc:#010x} stored={stored:#010x} match={calc==stored}')

def verify_probe():
    import struct
    p=open(os.path.join(DUMP,'work/filmgrain/sa_yknr_probeS.bin'),'rb').read()
    calc=sum32(p); stored=struct.unpack_from('<I',p,len(p)-4)[0]
    print(f'probeS sum32 calc={calc:#010x} stored={stored:#010x} match={calc==stored}')
