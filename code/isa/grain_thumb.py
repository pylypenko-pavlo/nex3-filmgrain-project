#!/usr/bin/env python3
"""ARMv6 Thumb-1 film-grain routine for the NEX-3N av-cam capture path.

Overwrites a capture stage (e.g. Stage_SoftFocus, which gets r0=ctx). Reads the
YC buffer base directly from the develop-session object (*(u32*)(r4+0x3e24), the
same value the accessor 0xc36045fc returns), then adds xorshift32 noise to the
first N bytes of the YUYV 4:2:2 buffer, clamped [0,255], returns r0=0 (stage
success). Pure 16-bit Thumb-1 only (ARM11/ARMv6: no movw/movt/usat/.w).

Delivery note: do NOT write this into live RAM via senser — exiting service mode
reboots the camera and reverts the patch before any capture. Bake it into
/system/av-cam.bin and deliver by file (FileControl). See notes/grain-hook.md.

Needs keystone (brew install keystone; DYLD_LIBRARY_PATH=$HOMEBREW_PREFIX/lib, /opt/homebrew by default).
"""
import os
os.environ.setdefault('DYLD_LIBRARY_PATH', os.environ.get('HOMEBREW_PREFIX', '/opt/homebrew') + '/lib')
import keystone, capstone

# region bytes (0x80<<16 = 8MB) and amplitude (and #0x3f, sub #0x1f = +/-31) are tunable
ASM = r'''
  push {r4,r5,r6,r7,lr}
  ldr  r4, [r0]            ; r4 = *ctx (develop session)
  movs r0, #0x3e
  lsls r0, r0, #8
  adds r0, #0x24           ; r0 = 0x3e24
  ldr  r6, [r4, r0]        ; r6 = buffer base = *(u32*)(session+0x3e24)
  movs r1, #0x80
  lsls r1, r1, #16         ; r1 = 0x800000 (8MB region)
  mov  r2, r6
  adds r2, #1              ; prng seed = base+1
  movs r3, #0             ; i
loop:
  cmp  r3, r1
  bhs  done
  lsls r0, r2, #13
  eors r2, r0
  lsrs r0, r2, #17
  eors r2, r0
  lsls r0, r2, #5
  eors r2, r0             ; xorshift32 in r2
  ldrb r0, [r6, r3]
  movs r5, #0x3f
  ands r5, r2
  subs r5, #0x1f          ; noise -31..32
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
  movs r0, #0            ; stage success
  pop  {r4,r5,r6,r7,pc}
'''

def assemble(base_va=0xc37ea898):
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(ASM, addr=base_va)
    blob = bytes(code)
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    bad = [i for i in md.disasm(blob, base_va) if i.size != 2]
    assert not bad, "non-16-bit (Thumb-2) instruction present: %r" % [(hex(i.address), i.mnemonic) for i in bad]
    return blob

if __name__ == '__main__':
    blob = assemble()
    print('grain routine: %d bytes, all 16-bit' % len(blob))
    print(blob.hex())

# Verified assembled bytes (region 8MB, amplitude +/-31), base 0xc37ea898:
#   f0b504683e20000224302658802109043246013200238b4213d250034240500c42
#   4050014240f05c3f2515401f3d401903d4ff2802d9ff2000e00020f0540133e9e7
#   0020f0bd
# (70 bytes, all 16-bit Thumb-1; identical ASM verified via keystone+capstone.)
