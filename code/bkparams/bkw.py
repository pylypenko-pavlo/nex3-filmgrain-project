import sys,io,struct
sys.path.insert(0,__import__('os').environ.get('PMCA_RE','Sony-PMCA-RE'))
from pmca.backup import BackupFile
fn=__import__('os').environ['NEX3N_BACKUP']
f=BackupFile(io.BytesIO(open(fn,'rb').read()));P=dict(f.listProperties())
def blk(k): return P[k].data
if __name__=='__main__':
  for a in sys.argv[1:]:
    k=int(a,16); d=P[k].data
    print('== %08x len %d'%(k,len(d)))
    for o in range(0,len(d),32):
        w=struct.unpack_from('<%dH'%(min(32,len(d)-o)//2),d,o)
        print('  +%03x: '%o+' '.join('%5x'%x for x in w))
