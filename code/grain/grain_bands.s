; grain_bands: leaf routine (bl / ret). r13 = engine tile window (end-of-tile ptr).
; Amplitude chosen by horizontal BAND = (global tile counter >> 11), capped 0..7.
; RAM (inside the loaded routine image, base r6):
;   CNT=base+0 u32 counter(baked 0); Ntab=base+4 {0,2,3,4,6,8,12,16}; Mtab=base+12 {0,3,7,7,15,15,31,31}
grain:
    mov  r6,#0x5f
    lsl  r6,#8          ; r6 = RAM base (&CNT) ; placement-patched
    ldr  r0,[r6]
    add  r0,#1
    str  r0,[r6]        ; counter++
    lsr  r0,#11         ; r0 = band candidate
    mov  r7,#7
    cmp.gtu r0,r7
    bfc  bandok
    mov  r0,r7          ; cap band at 7
bandok:
    mov  r7,r6
    add  r7,#4          ; &Ntab
    ldrb r4,[r7,r0]     ; r4 = N
    mov  r7,r6
    add  r7,#12         ; &Mtab
    ldrb r5,[r7,r0]     ; r5 = mask
    mov  r0,#1
    lsl  r0,#11
    mov  r1,r13
    sub  r1,r0          ; r1 = tile start
    mov  r3,r1          ; LFSR seed
loop:
    cmp.gtu r13,r1
    bfc  done
    mov  r2,r3
    lsl  r2,#13
    eor  r3,r2
    mov  r2,r3
    lsr  r2,#17
    eor  r3,r2
    mov  r2,r3
    lsl  r2,#5
    eor  r3,r2
    mov  r0,r3
    and  r0,r5          ; lfsr & mask
    sub  r0,r4          ; - N  -> signed noise
    ldrb r2,[r1]
    add  r2,r0
    mov  r0,#0
    cmp.ges r2,r0
    bfs  chkhi
    mov  r2,r0
chkhi:
    mov  r0,#-1
    uxtb r0,r0
    cmp.gts r2,r0
    bfc  store
    mov  r2,r0
store:
    strb r2,[r1]
    add  r1,#2
    b    loop
done:
    ret
