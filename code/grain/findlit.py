import sys,struct
b=open(sys.argv[1],'rb').read()
targets=[0x48200,0x48204,0x48208,0x4820c,0x48210,0x48220,0x48228,0x48230,0x48234,0x48238,
         0x40000,0x40078,0x4000,0x31d0,0x348c,0x800]
for t in targets:
    needle=struct.pack('<I',t)
    offs=[]
    i=0
    while True:
        j=b.find(needle,i)
        if j<0: break
        offs.append(j); i=j+1
    if offs:
        print(f"{t:#08x}: "+", ".join(hex(o) for o in offs))
