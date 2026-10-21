import struct,os,glob
import numpy as np
NOP=0x1f70fb87dc3ee1f7
D=os.environ.get('NEX3N_SABIN','sabin')
D3=os.environ.get('NEX3N_SABIN3','sabin3')
def files():
    return sorted(glob.glob(D+'/sa_*.bin'))+sorted(glob.glob(D3+'/*.bin'))
def blocks(b):
    """VLIW blocks: runs of 8-aligned qwords seeded by NOP bundles. A block starts at a NOP-run
    and extends forward until a zero qword or a qword run that looks scalar (heuristic: 3 consecutive
    qwords with HD(NOP)>=26 AND not in 'bfff' family AND not in 'f1c7' family) — kept simple."""
    n=len(b)//8
    q=np.frombuffer(b[:n*8],dtype='<u8')
    isnop=np.where(q==NOP)[0]
    return q,isnop
def hd(x,y=NOP): return bin(int(x)^y).count('1')
