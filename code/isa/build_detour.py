import os,struct
os.environ.setdefault('DYLD_LIBRARY_PATH',os.environ.get('HOMEBREW_PREFIX','/opt/homebrew')+'/lib')
import keystone, capstone
ks=keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
md=capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
BASE=0xc3441000
AV=bytearray(open(os.environ['NEX3N_AVCAM'],'rb').read())

HOOK=0xc3889772           # overwrite 10 bytes here (mov r0,r5; bl 0xc3722494; cmp r0,#0; beq 0xc388981a)
C=0xc3a011c0              # cave base (stub)
GRAIN=C+36               # grain routine right after 36-byte stub
BACK=0xc388977c          # return point (after the beq)
ESC=0xc388981a           # gate-fail target (original beq dest)

def asm(code, addr):
    b,_=ks.asm(code, addr=addr); return bytes(b)

# ---- grain routine (+-15, 8MB), pure Thumb-1 ----
GRAIN_ASM = r'''
  push {r4,r5,r6,r7,lr}
  ldr  r4, [r0]
  movs r0, #0x3e
  lsls r0, r0, #8
  adds r0, #0x24
  ldr  r6, [r4, r0]
  movs r1, #0x80
  lsls r1, r1, #16
  mov  r2, r6
  adds r2, #1
  movs r3, #0
loop:
  cmp  r3, r1
  bhs  done
  lsls r0, r2, #13
  eors r2, r0
  lsrs r0, r2, #17
  eors r2, r0
  lsls r0, r2, #5
  eors r2, r0
  ldrb r0, [r6, r3]
  movs r5, #0x1f
  ands r5, r2
  subs r5, #0xf
  adds.n r0, r0, r5
  bmi  clamp0
  cmp  r0, #255
  bls  store
  movs r0, #255
  b    store
clamp0:
  movs r0, #0
store:
  strb r0, [r6, r3]
  adds r3, #1
  b    loop
done:
  movs r0, #0
  pop  {r4,r5,r6,r7,pc}
'''
grain = asm(GRAIN_ASM, GRAIN)
assert all(i.size==2 for i in md.disasm(grain,GRAIN)), "grain has wide instr"

# ---- stub (28 bytes of instrs + 8 bytes literals = 36) ----
STUB_ASM = f'''
  push {{r0,r1,r2,r3}}
  mov  r0, r5
  bl   #{GRAIN}
  pop  {{r0,r1,r2,r3}}
  mov  r0, r5
  bl   #0xc3722494
  cmp  r0, #0
  bne  #{C+24}
  ldr  r3, [pc, #4]
  bx   r3
  ldr  r3, [pc, #4]
  bx   r3
'''
stub_instrs = asm(STUB_ASM, C)
assert len(stub_instrs)==28, "stub instr len=%d (want 28)"%len(stub_instrs)
stub = stub_instrs + struct.pack('<II', ESC|1, BACK|1)   # ESC .word @C+28, BACK .word @C+32
assert len(stub)==36

# ---- trampoline at HOOK (10 bytes): ldr r3,[pc,#4]; bx r3; 0000; .word STUB|1 ----
tramp_instrs = asm('ldr r3,[pc,#4]\n bx r3', HOOK)
assert len(tramp_instrs)==4
tramp = tramp_instrs + b'\x00\x00' + struct.pack('<I', C|1)
assert len(tramp)==10

# ---- apply patches ----
def put(va, blob):
    o=va-BASE; AV[o:o+len(blob)]=blob
put(C, stub)
put(GRAIN, grain)
put(HOOK, tramp)

out=os.environ.get('NEX3N_AVCAM_OUT','av-cam_grain.bin')
open(out,'wb').write(AV)
print('patched av-cam written:', out, len(AV),'bytes')
print('cave stub @%#x, grain @%#x, hook @%#x'%(C,GRAIN,HOOK))

# ---- verify by disassembly ----
def show(va,n,label):
    print('---',label,'---'); o=va-BASE
    for ins in md.disasm(bytes(AV[o:o+n]),va):
        print('  %08x: %-7s %s'%(ins.address,ins.mnemonic,ins.op_str))
show(HOOK,12,'trampoline @HOOK')
print('  .word at %#x = %08x'%(HOOK+6, struct.unpack_from('<I',AV,HOOK+6-BASE)[0]))
show(C,28,'stub instrs')
print('  ESC .word @%#x = %08x ; BACK .word @%#x = %08x'%(C+28,struct.unpack_from('<I',AV,C+28-BASE)[0],C+32,struct.unpack_from('<I',AV,C+32-BASE)[0]))
show(GRAIN,20,'grain head')
