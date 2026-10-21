import os,sys,hashlib,io
os.environ.setdefault('DYLD_LIBRARY_PATH',os.environ.get('HOMEBREW_PREFIX','/opt/homebrew')+'/lib')
import keystone,capstone
sys.path.insert(0,os.environ['NEX3N_LZPT_DIR'])
sys.path.insert(0,os.environ['NEX3N_FWTOOL'])
from lzpt_write import write_lzpt
from fwtool.archive import lzpt
ks=keystone.Ks(keystone.KS_ARCH_ARM,keystone.KS_MODE_THUMB)
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB)
BASE=0xc3441000; CAVE=0xc3a011c0; SF=0xc37ea898; AVOFF=0x8e00; PART=10485760
SITES=[0xc36282a2,0xc36282e4,0xc3628324,0xc362836c,0xc36286a0,0xc36286e2,0xc3628722,0xc362876a]
INNER=bytearray(open(os.environ['NEX3N_P3_INNER'],'rb').read())
SYS=open(os.environ['NEX3N_AVCAM'],'rb').read()
CURVE=SYS[0x5b006a:0x5b0072]

def region_instrs(region):
    for s in range(0,25):
        if region%(1<<s)==0 and (region>>s)<=0xff:
            return f'movs r1,#{region>>s}\n  lsls r1,r1,#{s}'
    raise ValueError(hex(region))

def wrapper_asm(call_sf, lm,ls,cm,cs, region):
    pre = f'bl #{SF}\n  mov r7,r0' if call_sf else ''
    ret = 'mov r0,r7' if call_sf else 'movs r0,#0'
    return f'''
      push {{r4,r5,r6,r7,lr}}
      mov  r4,r0
      {pre}
      ldr  r5,[r4]
      movs r0,#0x5
      lsls r0,r0,#8
      adds r0,#0xe4
      ldr  r6,[r5,r0]
      movs r0,#0xc0
      lsls r0,r0,#24
      orrs r6,r0
      {region_instrs(region)}
      mov  r2,r6
      adds r2,#1
      movs r3,#0
    loop:
      cmp  r3,r1
      bhs  done
      lsls r0,r2,#13
      eors r2,r0
      lsrs r0,r2,#17
      eors r2,r0
      lsls r0,r2,#5
      eors r2,r0
      ldrb r0,[r6,r3]
      movs r4,#1
      ands r4,r3
      bne  chroma
      movs r4,#{lm}
      ands r4,r2
      subs r4,#{ls}
      b    addn
    chroma:
      movs r4,#{cm}
      ands r4,r2
      subs r4,#{cs}
    addn:
      adds.n r0,r0,r4
      bmi  cl0
      cmp  r0,#255
      bls  st
      movs r0,#255
      b    st
    cl0:
      movs r0,#0
    st:
      strb r0,[r6,r3]
      adds r3,#1
      b    loop
    done:
      {ret}
      pop {{r4,r5,r6,r7,pc}}
    '''

def build(name, call_sf, lm,ls,cm,cs, region):
    asm=wrapper_asm(call_sf,lm,ls,cm,cs,region)
    wrap=bytes(ks.asm(asm,addr=CAVE)[0])
    bad=[hex(i.address) for i in md.disasm(wrap,CAVE) if i.size!=2 and i.mnemonic not in('bl','blx')]
    assert not bad,(name,bad)
    assert CAVE-BASE+len(wrap)<0x5c01bd+3442
    av=bytearray(SYS)
    av[CAVE-BASE:CAVE-BASE+len(wrap)]=wrap
    for s in SITES: av[s-BASE:s-BASE+4]=bytes(ks.asm('bl #%d'%CAVE,addr=s)[0])
    av=bytes(av)
    assert av[0x5b006a:0x5b0072]==CURVE
    inner=bytearray(INNER); inner[AVOFF:AVOFF+len(av)]=av
    img=write_lzpt(bytes(inner)); img+=b'\xff'*(PART-len(img))
    dec=list(lzpt.readLzpt(io.BytesIO(img)))[0].contents.read()
    assert dec[AVOFF:AVOFF+len(av)]==av,'decompress'
    open('p3_%s.bin'%name,'wb').write(img)
    print('%-14s L+-%d C+-%d %s md5=%s'%(name,ls,cs,'SF+grain' if call_sf else 'pure',hashlib.md5(img).hexdigest()))

if __name__=='__main__':
    FULL=0x1E00000; SAFE=0x800000
    # name, callSF, Lmask,Lsub, Cmask,Csub, region
    build('lowiso',   False, 15,7,   3,1,  FULL)   # ISO100-200 fine
    build('iso400',   False, 31,15,  7,3,  FULL)   # ISO400 classic
    build('iso800',   False, 63,31,  7,3,  FULL)   # ISO800
    build('highiso',  False, 127,63, 15,7, FULL)   # ISO1600-3200 heavy
    build('softdream',True,  31,15,  7,3,  FULL)   # soft focus + grain
    build('iso400_8mb',False,31,15,  7,3,  SAFE)   # fallback (watchdog-safe)
    print('ALL DONE')
