import sys,io
sys.path.insert(0,__import__('os').environ.get('PMCA_RE','Sony-PMCA-RE'))
from pmca.backup import BackupFile
fn=sys.argv[1] if sys.argv[1].endswith('.bin') else __import__('os').environ['NEX3N_BACKUP']
args=sys.argv[2:] if sys.argv[1].endswith('.bin') else sys.argv[1:]
f=BackupFile(io.BytesIO(open(fn,'rb').read()));P=dict(f.listProperties())
for a in args:
    k=int(a,16); d=P[k].data
    print('== %08x attr %02x len %d'%(k,P[k].attr,len(d)))
    for o in range(0,len(d),32):
        print('  +%03x: '%o+' '.join(d[o+i:o+i+2].hex() for i in range(0,min(32,len(d)-o),2)))
