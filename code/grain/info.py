import sys,os
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','isa'))
from mod import Mod, images
path=sys.argv[1]
b=open(path,'rb').read()
print("file len", hex(len(b)), "magic", b[:4].hex(), "ver", b[4])
ims=images(b)
print("images:", [(hex(o),n) for o,n in ims])
m=Mod(path, d=os.path.dirname(path), img=0)
print("desc", hex(m.desc))
print("w[]:", [hex(x) for x in m.w])
print("tbase(file)", hex(m.tbase), "tend(file)", hex(m.tend), "textlen", hex(len(m.t)))
# file offsets of interest -> text-relative
for fo in [0xac50,0xac58,0xac70,0xaf4a, 0xd100, len(b)-4]:
    print(f"file {fo:#x} -> text {fo-m.tbase:#x}")
