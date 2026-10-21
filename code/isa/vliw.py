import struct,sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from mod import Mod,images
NOP=0x1f70fb87dc3ee1f7
MODS=['sa_sftfcs.bin','sa_tbox.bin','sa_yknr.bin','sa_jpeg_enc_1core.bin','sa_defect.bin','sa_kknr.bin','sa_spica.bin','sa_star.bin','sa_apollo4.bin']
def regions(m):
    """find 8-aligned runs that contain the NOP bundle; return list of (start,end) in text"""
    t=m.t; n=len(t); out=[]; a=0
    # scan 8-aligned; a bundle-region = contiguous 8-aligned words where NOPs appear
    words=[(i,struct.unpack_from('<Q',t,i)[0]) for i in range(0,n-7,8)]
    nops=[i for i,w in words if w==NOP]
    if not nops: return out
    s=nops[0]; e=nops[-1]+8
    # extend start back while plausible bundles (nonzero, not ascii-ish). crude: back to previous 0-run
    while s-8>=0:
        w=struct.unpack_from('<Q',t,s-8)[0]
        if w==0: break
        s-=8
    return [(s,e)]
def allbundles():
    B=[]
    for n in MODS:
        for img in range(len(images(open(Mod.__init__.__defaults__ and 0 or 0,).__class__ and 0 or 0)) if False else range(0,0)):
            pass
    return B
