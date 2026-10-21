import sys,struct
D=open(__import__('os').environ['NEX3N_AVCAM'],'rb').read()
def bl_targets(tgt):
    out=[]
    for a in range(0,len(D)-4,2):
        h1,h2=struct.unpack_from('<HH',D,a)
        if (h1&0xf800)==0xf000 and (h2&0xe800)==0xe800:
            off=((h1&0x7ff)<<12)|((h2&0x7ff)<<1)
            if off&0x400000: off-=0x800000
            t=a+4+off
            if (h2&0x1000)==0: t&=~3  # blx
            if t==tgt: out.append(a)
    return out
for x in sys.argv[1:]: print(x,[hex(a) for a in bl_targets(int(x,16))])
