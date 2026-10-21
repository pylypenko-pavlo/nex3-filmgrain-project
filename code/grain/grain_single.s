grain:
    mov  r0,#1
    lsl  r0,#11
    mov  r1,r13
    sub  r1,r0
    mov  r3,r1
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
    mov  r4,r3
    mov  r0,#0x0f
    and  r4,r0
    mov  r0,#8
    sub  r4,r0
    ldrb r5,[r1]
    add  r5,r4
    mov  r0,#0
    cmp.ges r5,r0
    bfs  chkhi
    mov  r5,r0
chkhi:
    mov  r0,#-1
    uxtb r0,r0
    cmp.gts r5,r0
    bfc  store
    mov  r5,r0
store:
    strb r5,[r1]
    add  r1,#2
    b    loop
done:
    ret
