import sys,struct,capstone
D=open(__import__('os').environ['NEX3N_AVCAM'],'rb').read()
def litrefs(L):
    out=[]
    for A in range(max(0,L-1024),L,2):
        h=struct.unpack_from('<H',D,A)[0]
        if (h&0xf800)==0x4800 and ((A+4)&~3)+(h&0xff)*4==L: out.append(('T',A))
    for A in range(max(0,L-4096)&~3,L,4):
        w=struct.unpack_from('<I',D,A)[0]
        if (w&0x0f7f0000)==0x051f0000:
            imm=w&0xfff; t=A+8+(imm if w&0x800000 else -imm)
            if t==L: out.append(('A',A))
    return out
def dis(a0,a1,mode='T'):
    md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB if mode=='T' else capstone.CS_MODE_ARM)
    for i in md.disasm(D[a0:a1],a0): print("%x: %s %s"%(i.address,i.mnemonic,i.op_str))
if __name__=='__main__':
    if sys.argv[1]=='r':
        for x in sys.argv[2:]: print(x,[(m,hex(a)) for m,a in litrefs(int(x,16))])
    else: dis(int(sys.argv[2],16),int(sys.argv[3],16),sys.argv[1])
