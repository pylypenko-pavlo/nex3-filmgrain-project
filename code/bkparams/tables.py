import struct
from trace import P
RAM={}
import pickle
A,B,R=pickle.load(open(__import__('os').environ['NEX3N_ADJMAP'],'rb'))
mem={}
for a,r in zip(A,R):
    for i,b in enumerate(P[a].data): mem[r+i]=b
base={a:r for a,r in zip(A,R)}
def tab(blk,off,n=11,sz=2):
    r=base[blk]+off
    return [int.from_bytes(bytes(mem[r+i*sz+j] for j in range(sz)),'little') for i in range(n)]
T={
 'sel3 e0':(0x30049,0x16),'sel3 f4':(0x30049,0x42),'sel3 hi_cor_gainth':(0x30049,0x6e),'sel3 [104]':(0x30049,0x9a),'sel3 hi_gain_cn':(0x30049,0xc6),'sel3 hi_gain_eg':(0x3004a,0x0),
 'sel1 e0':(0x30049,0x0),'sel1 f4':(0x30049,0x2c),'sel1 hi_cor_gainth':(0x30049,0x58),'sel1 [104]':(0x30049,0x84),'sel1 hi_gain_cn':(0x30049,0xb0),'sel1 hi_gain_eg':(0x30049,0xdc),
 'sel2 e0':(0x30014,0x6a),'sel2 f4':(0x30015,0x52),'sel2 hi_cor_gainth':(0x30015,0x9e),'sel2 [104]':(0x30015,0xf2),'sel2 hi_gain_cn':(0x30016,0xd8),'sel2 hi_gain_eg':(0x30017,0x24),
 'sel0 e0':(0x3011f,0x6e),'sel0 f4':(0x3011f,0x84),'sel0 hi_cor_gainth':(0x3011f,0x9a),'sel0 [104]':(0x3011f,0xb0),'sel0 hi_gain_cn':(0x3011f,0xc6),'sel0 hi_gain_eg':(0x3011f,0xdc),
 'gainth_cn':(0x30013,0x2c),'gainth_eg':(0x30013,0x78),'ofstth_cn':(0x30013,0xc4),'ofstth_eg':(0x30014,0x10),
 'lgst':(0x30014,0xba),'lggrad':(0x30015,0x6),'hi_cor_limth':(0x30016,0x3e),'hi_gain_min':(0x30016,0x8a),
 'YAP apgain':(0x3000c,0x1c),'YAP vcoring_p0':(0x3000c,0xce),'YAP hcoring_p0':(0x3000d,0x5e),
 'Apacon ISO mult (78b0)':(0x30106,0x0),
 'X axis NR/YAP':(0x3000c,0x6),'X axis Apacon':(0x30108,0xa0),
}
for k,(b,o) in T.items(): print('%-24s %05x+0x%02x  %s'%(k,b,o,' '.join('%x'%v for v in tab(b,o))))
print('ladder 78b0 30106+0xac:', ' '.join('%d'%v for v in tab(0x30106,0xac,9)))
print('ladder 78b4 30106+0xbe:', ' '.join('%d'%v for v in tab(0x30106,0xbe,9)))
print('toy curve 30040+0xa2:', ' '.join('%x'%v for v in tab(0x30040,0xa2,32)))
