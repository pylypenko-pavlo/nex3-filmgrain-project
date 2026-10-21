import sys,capstone
AV=__import__('os').environ['NEX3N_AVCAM']
d=open(AV,"rb").read()
a0=int(sys.argv[1],16); a1=int(sys.argv[2],16)
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB)
for i in md.disasm(d[a0:a1],a0): print("%x: %-8s %s"%(i.address,i.mnemonic,i.op_str))
