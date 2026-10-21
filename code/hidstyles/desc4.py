import sys,re,os,struct
from elfx import X
x=X(sys.argv[1]); a0=int(sys.argv[2],16); n=int(sys.argv[3]); st=int(sys.argv[4],16) if len(sys.argv)>4 else 0x28
sd=open(os.path.expanduser('~/nex3n-dump/work/out3n/nflasha8_unpacked_unpacked/share/app/string_english.uxc'),'rb').read()
names={}
for m in re.finditer(rb'(..)\x00\x1e([^\x00]{1,70})\x00',sd,re.S): names.setdefault(int.from_bytes(m.group(1),'little'),m.group(2).decode('utf8','replace'))
def nm(w): return names.get(w&0xffff,'') if (w>>16)==0x200 else ''
for k in range(n):
    a=a0+st*k; ws=[x.u32(a+4*i) for i in range(st//4)]
    print('%x'%a,' '.join('%08x'%w for w in ws),' | ',' / '.join(filter(None,[nm(w) for w in ws]))[:90])
