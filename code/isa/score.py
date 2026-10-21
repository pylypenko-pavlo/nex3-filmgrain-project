import subprocess,re,sys
OD=__import__('os').environ.get('OBJDUMP','objdump')
f=__import__('os').path.join(__import__('os').environ.get('NEX3N_SABIN','sabin'),'sa_sftfcs.bin'); s=0x320; e=0x2c00
# canonical epilogue + prologue snippet
snip=bytes.fromhex('8f189f18af18bf18cf18df18ef18df00'+'cf00fe0cfd0cfc0cfb0cfa0cf90cf80c03000000')
open('snip.bin','wb').write(snip)
archs=[('mep',[]),('sh',['-EL']),('sh',['-EB']),('arm',['-EL','-M','force-thumb']),('MCore',['-EL']),('MCore',['-EB']),('csky',['-EL']),('m32r',['-EB']),('fr30',['-EB']),('v850e',['-EL']),('rx',['-EL']),('mn10300',['-EL']),('xstormy16',['-EL']),('cr16',['-EL']),('d10v',['-EB']),('tic6x',['-EL']),('bfin',['-EL']),('msp430',['-EL']),('ARCv2',['-EL']),('ARC700',['-EL']),('xtensa',['-EL']),('epiphany16',['-EL']),('tms320c54x',['-EL']),('pru',['-EL']),('riscv:rv32',['-EL']),('h8300s',['-EB']),('cris',['-EL']),('avr',['-EL']),('m68k',['-EB']),('z8002',['-EB']),('rl78',['-EL']),('m16c',['-EL']),('ft32',['-EL']),('moxie',['-EL']),('ms1',['-EB']),('nds32',['-EL']),('or1k',['-EB']),('microblaze',['-EB'])]
bad=re.compile(r'\.word|\.short|unknown|\(bad\)|\.byte|undefined|illegal|invalid|\.long|\?\?\?|reserved|excw',re.I)
for m,o in archs:
    r=subprocess.run([OD,'-D','-b','binary','-m',m]+o+[f'--start-address={s}',f'--stop-address={e}',f],capture_output=True,text=True)
    L=[l for l in r.stdout.splitlines() if re.match(r'\s+[0-9a-f]+:\t',l)]
    nb=sum(1 for l in L if bad.search(l))
    r2=subprocess.run([OD,'-D','-b','binary','-m',m]+o+['snip.bin'],capture_output=True,text=True)
    S=[l.split('\t')[-1].strip() for l in r2.stdout.splitlines() if re.match(r'\s+[0-9a-f]+:\t',l)]
    print(f'{m+" ".join(o):24s} lines={len(L):5d} bad={100*nb/max(1,len(L)):5.1f}%  epi: {" | ".join(S[8:13]) if len(S)>12 else S[-5:]} ;; ret: {S[-2] if len(S)>1 else "-"}'[:230], r.stderr[:60].strip())
