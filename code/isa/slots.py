NOP=0x1f70fb87dc3ee1f7
PARTS=[(63,52),(51,39),(38,26),(25,13),(12,0)]
def slots(w): return [(w>>lo)&((1<<(hi-lo+1))-1) for hi,lo in PARTS]
def fmt(w): return ' '.join(f'{s:04x}' for s in slots(w))
