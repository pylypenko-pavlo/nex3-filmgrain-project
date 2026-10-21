import struct,os,glob
NOP=0x1f70fb87dc3ee1f7
NOPB=struct.pack('<Q',NOP)
ROOT=os.environ.get('SONY_SABIN_ROOT','sabin_root')
GEN={'3N':ROOT+'/3N','NEX6':ROOT+'/sabin_nex6','6000':ROOT+'/sabin_6000V321',
     '7M2':ROOT+'/sabin_7M2V401','7M3':ROOT+'/sabin_7M3V401','6400':ROOT+'/sabin_6400V200'}
def raw(g,n):
    p=f'{GEN[g]}/{n}'
    return open(p,'rb').read() if os.path.exists(p) else None
def nops(b):
    out=[];i=b.find(NOPB)
    while i>=0: out.append(i); i=b.find(NOPB,i+1)
    return out
def region(b):
    """VLIW region: from first NOP (mod 8 phase) back to a zero qword, forward to last NOP + run of nonzero"""
    ns=nops(b)
    if not ns: return None
    ph=ns[0]%8
    s=ns[0]
    while s-8>=0 and b[s-8:s]!=b'\0'*8: s-=8
    e=ns[-1]+8
    while e+8<=len(b) and b[e:e+8]!=b'\0'*8: e+=8
    return s,e,ph
def bundles(b):
    r=region(b)
    if not r: return []
    s,e,_=r
    return [struct.unpack_from('<Q',b,i)[0] for i in range(s,e,8)]
