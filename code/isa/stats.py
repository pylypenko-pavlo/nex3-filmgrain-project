import os,collections,math,struct
D=__import__('os').environ.get('NEX3N_SABIN','sabin')
c=collections.Counter(); pos=[collections.Counter() for _ in range(4)]
tot=0
for n in os.listdir(D):
    if not n.startswith('sa_'): continue
    b=open(f'{D}/{n}','rb').read()[0x16a:-4]
    for i in range(0,len(b)-1,2):
        h=b[i]|b[i+1]<<8; c[h]+=1; tot+=1
    for i,x in enumerate(b): pos[i%4][x]+=1
def H(cn): s=sum(cn.values()); return -sum(v/s*math.log2(v/s) for v in cn.values())
print('entropy by pos mod4', [round(H(p),2) for p in pos])
print('top halfwords (LE value):')
for h,v in c.most_common(60): print(f'{h:04x} {v} {100*v/tot:.2f}%')
