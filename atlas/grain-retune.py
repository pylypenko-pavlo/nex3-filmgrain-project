"""Retune the grain to REAL ultramax400 scans: finer kernel + weaker sigma. Apply to the camera fixture,
compare grain (size+strength) to a real scan crop, 1:1. Iterate SCALE/kernel via args."""
import os, sys, io, glob, numpy as np
from PIL import Image, ImageDraw, ImageFilter
F=os.environ.get('NEX3N_PHOTOS','fixtures')   # test frames / fixtures dir
SCALE=float(sys.argv[1]) if len(sys.argv)>1 else 0.42   # amplitude vs the NDG hump (peak 8.8 -> 8.8*SCALE)
KERN=[int(x) for x in (sys.argv[2].split(',') if len(sys.argv)>2 else '1,4,1'.split(','))]
CHROMA=float(sys.argv[3]) if len(sys.argv)>3 else 0.30
MV=np.array([8,24,40,56,72,88,104,120,135,152,168,184,200,216,232,248])
SY=np.array([0.19,1.52,3.37,5.27,6.98,8.29,8.79,8.74,8.06,6.90,5.50,3.79,2.24,1.15,0.39,0.00])*SCALE
SCB=np.array([0.02,0.79,2.35,3.45,4.32,4.87,5.11,5.16,4.41,3.72,2.60,1.85,1.19,0.62,0.13,0.00])*SCALE*CHROMA/0.30*0.30
SCR=np.array([0.02,0.46,1.21,2.08,2.60,3.01,3.06,2.95,2.79,2.24,1.63,1.36,0.47,0.48,0.11,0.00])*SCALE*CHROMA/0.30*0.30
def lut(sv):
    x=np.arange(256); y=np.interp(x,MV,sv,left=0,right=0); y[:8]=np.interp(np.arange(8),[0,8],[0,sv[0]]); return np.clip(y,0,None).astype(np.float32)
LY,LCB,LCR=lut(SY),lut(SCB*CHROMA),lut(SCR*CHROMA)
K=np.array(KERN,np.float32)
def conv1(n,ax):
    k=K/K.sum(); c=len(K)//2; out=np.zeros_like(n)
    for j,w in enumerate(k): out=out+w*np.roll(n,j-c,ax)
    return out
def blur(n,passes=1):
    for _ in range(passes): n=conv1(conv1(n,0),1)
    return n
def composite(rgb,seed=11):
    ycc=np.asarray(Image.fromarray(rgb).convert('YCbCr'),np.float32); Y=ycc[:,:,0]; H,W=Y.shape
    rng=np.random.default_rng(seed)
    nb=blur(rng.standard_normal((H,W)).astype(np.float32),1); nb/=nb.std()+1e-6
    ncb=blur(rng.standard_normal((H,W)).astype(np.float32),2); ncb/=ncb.std()+1e-6
    ncr=blur(rng.standard_normal((H,W)).astype(np.float32),2); ncr/=ncr.std()+1e-6
    Yi=np.clip(Y,0,255).astype(int); out=ycc.copy()
    out[:,:,0]=np.clip(Y+LY[Yi]*nb,0,255)
    out[:,:,1]=np.clip(ycc[:,:,1]+LCB[Yi]*ncb,0,255)
    out[:,:,2]=np.clip(ycc[:,:,2]+LCR[Yi]*ncr,0,255)
    rgb2=np.asarray(Image.fromarray(out.astype(np.uint8),'YCbCr').convert('RGB'))
    b=io.BytesIO(); Image.fromarray(rgb2).save(b,'JPEG',quality=94); b.seek(0)
    return np.asarray(Image.open(b).convert('RGB'))
def sigY(ref,img,y0,x0,s=180):
    a=np.asarray(Image.fromarray(ref[y0:y0+s,x0:x0+s]).convert('YCbCr'),np.float32)[:,:,0]
    b=np.asarray(Image.fromarray(img[y0:y0+s,x0:x0+s]).convert('YCbCr'),np.float32)[:,:,0]
    return float(a.mean()),float((b-a).std())
# camera fixture grained with the retune
clean=np.asarray(Image.open(F+'/DSC09580.JPG').convert('RGB'))
mine=composite(clean)
# real ultramax scan flat crop (a midtone region) for visual grain comparison
scanfs=sorted(glob.glob(os.path.join(os.environ.get('NEX3N_SCANS','scans'),'pos/ultramax400-euro-1/*.jpg')))
scan=np.asarray(Image.open(scanfs[18]).convert('RGB'))
# measure scan grain on a flat patch
sy=np.asarray(Image.open(scanfs[18]).convert('YCbCr'),np.float32)[:,:,0]
H,W=sy.shape; best=None
for y in range(0,H-180,180):
  for x in range(0,W-180,180):
    p=sy[y:y+180,x:x+180]; m=p.mean()
    if m<60 or m>190: continue
    lv=p[::8,::8].var()
    if best is None or lv<best[0]: best=(lv,x,y,m)
_,sx,syy,sm=best
scrop=scan[syy:syy+180,sx:sx+180]
sgrain=(np.asarray(Image.fromarray(scrop).convert('YCbCr'),np.float32)[:,:,0])
sgrain=sgrain-np.asarray(Image.fromarray(sgrain.astype('uint8')).filter(ImageFilter.GaussianBlur(2.0)),np.float32)
m,smine=sigY(clean,mine,1750,1150)
print('SCALE=%.2f KERN=%s CHROMA=%.2f  -> my grey(meanY=%.0f) sigY=%.2f   real-scan flat(meanY=%.0f) grain-std=%.2f'%(
    SCALE,KERN,CHROMA,m,smine,sm,sgrain.std()))
# side-by-side 1:1: clean camera | my retuned | real ultramax scan
cc=Image.fromarray(clean[1700:2060,1100:1460]); mm=Image.fromarray(mine[1700:2060,1100:1460]); ss=Image.fromarray(scrop).resize((360,360))
bar=18; W2=360
cmp=Image.new('RGB',(W2*3+12,360+bar),(25,25,25)); d=ImageDraw.Draw(cmp)
for i,(nm,t) in enumerate([('CLEAN cam',cc),('MY retuned',mm),('REAL ultramax scan',ss)]):
    x=i*(W2+6); cmp.paste(t,(x,bar)); d.text((x+4,3),nm,fill=(255,255,0))
cmp.save(F+'/_retune_cmp.png');
import shutil; shutil.copy(F+'/_retune_cmp.png', 'grain_retune_cmp.png')
print('saved _retune_cmp.png (+ ./grain_retune_cmp.png)')
