# find Thumb BL/BLX callers of target (file offsets), and literal refs to VA
import sys,struct
AV=__import__('os').environ['NEX3N_AVCAM']
d=open(AV,"rb").read(); BASE=0xc3441000
t=int(sys.argv[1],16)
for a in range(0,len(d)-4,2):
    h1,h2=struct.unpack_from('<HH',d,a)
    if (h1>>11)==0b11110 and (h2>>14)==0b11 and (h2>>12)&1 in (0,1):
        S=(h1>>10)&1; imm10=h1&0x3ff; J1=(h2>>13)&1; J2=(h2>>11)&1; imm11=h2&0x7ff
        I1=1-(J1^S); I2=1-(J2^S)
        off=(S<<24)|(I1<<23)|(I2<<22)|(imm10<<12)|(imm11<<1)
        if S: off-=1<<25
        x=(h2>>12)&1
        dest=a+4+off
        if not x: dest&=~3
        if dest==t: print("call from %x (%s)"%(a,'bl' if x else 'blx'))
va=t+BASE
for v in (va,va|1):
    i=d.find(struct.pack('<I',v))
    while i>=0: print("literal %x at %x"%(v,i)); i=d.find(struct.pack('<I',v),i+1)
