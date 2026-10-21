# NEX3N_DUMP: root of the firmware dump tree (default ./nex3n-dump)
import os,sys,struct,hashlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from saasm import asm
from build import STOCK,CORES,HOOK_OFF,ROUT_OFF,sum32,hook_bytes

# Probe-S fixed-marker logic, placed at chunk+0x13c, padded with NOP to 74 bytes (0xad8c..0xadd6).
# Identical placement/footprint to the bands routine; ONLY the code (marker vs loop) differs.
FOOT=0xadd6-0xad8c   # 74 bytes = bands routine footprint
MARKER = """
grain:
    add  sp,#0x50        ; displaced hook-site instruction (epilogue add sp,#0x50)
    mov  r0,#1
    lsl  r0,#11          ; r0 = 0x800
    mov  r1,r13          ; r1 = engine window (end of tile)
    sub  r1,r0           ; r1 = tile top-left = window - 0x800
    mov  r2,#-1          ; r2 = 0xFFFFFFFF (white)
    str  r2,[r1,#0]      ; marker word 0  (exact Probe S store encoding 0x7021)
    str  r2,[r1,#4]      ; marker word 1  (0x7121)
    b    0xaf4c          ; return into stock epilogue  (NO loop, NO LFSR)
"""
def routine_bytes(org):
    out,labels=asm(MARKER.splitlines(),org)
    bs=bytearray()
    for a,h in out: bs+=struct.pack('<H',h)
    # pad with NOP (0x0000) to the exact bands footprint
    assert len(bs)<=FOOT, (len(bs),FOOT)
    bs += b'\x00\x00'*((FOOT-len(bs))//2)
    assert len(bs)==FOOT
    return bytes(bs),labels

def build(out_path):
    buf=bytearray(open(STOCK,'rb').read())
    rb,labels=routine_bytes(CORES[0]+ROUT_OFF)   # org=core0 placement so 'b 0xaf4c' resolves
    hb=hook_bytes(CORES[0]+HOOK_OFF, CORES[0]+ROUT_OFF)
    ch=[]
    for base in CORES:
        rf=base+ROUT_OFF; hf=base+HOOK_OFF
        buf[rf:rf+len(rb)]=rb; ch.append((rf,rf+len(rb)))
        buf[hf:hf+2]=hb;       ch.append((hf,hf+2))
    s=sum32(buf); struct.pack_into('<I',buf,len(buf)-4,s)
    open(out_path,'wb').write(buf)
    return hashlib.md5(buf).hexdigest(),s,ch,labels,len(rb)

if __name__=='__main__':
    md5,s,ch,labels,rl=build(os.path.join(os.environ.get('NEX3N_DUMP','nex3n-dump'),'work/filmgrain/sa_yknr_probeS_reloc.bin'))
    print('md5',md5,'sum32',hex(s),'routine_len',rl,'footprint',hex(FOOT))
    print('labels',{k:hex(v) for k,v in labels.items()})
    print('changes',[(hex(a),hex(b)) for a,b in ch])
