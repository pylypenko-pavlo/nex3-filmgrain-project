from code import *
import collections
le=collections.Counter(); be=collections.Counter(); tot=0
for n,c in corpus():
    for i in range(0,len(c)-1,2):
        le[c[i]|c[i+1]<<8]+=1; be[c[i]<<8|c[i+1]]+=1; tot+=1
print('halfwords',tot)
for name,h in [('mep ret',0x7002),('sh rts',0x000b),('sh nop',0x0009),('thumb bx lr',0x4770),('csky rts',0x783c),('arc j_s blink',0x7ee0),('v850 jmp lp',0x006f),('xtensa ret.n',0xf00d),('bfin rts',0x0010),('rv c.ret',0x8082),('cf00',0x00cf),('df00',0x00df)]:
    print(f'{name:15s} LE {le[h]:6d}  BE {be[h]:6d}')
