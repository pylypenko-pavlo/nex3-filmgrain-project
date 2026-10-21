import os,struct
D=__import__('os').environ.get('NEX3N_SABIN','sabin')
def code(n):
    b=open(f'{D}/{n}','rb').read()
    v=b[4]|b[5]<<8
    w=struct.unpack_from('<12I',b,0x100)
    if w[0]&0xffff==0x3d and w[5]: return b[0x100:0x100+w[5]]
    return None
def corpus():
    for n in sorted(os.listdir(D)):
        if n.startswith('sa_'):
            c=code(n)
            if c: yield n,c
