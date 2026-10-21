"""Tune a FAST on-camera grain composite to match the filmgrain-cli ultramax400/0.15 reference.
Model (integer-portable to the C shim):
  n = white_noise(x,y,seed) -> separable blur k -> normalize to unit variance   (grain SIZE)
  Y' = clip(Y + sigmaY_LUT[Y] * n)                                               (granularity curve)
  Cb'= Cb + sigmaCb_LUT[Y] * n_c ;  Cr'= Cr + sigmaCr_LUT[Y] * n_c               (soft colour mottle, coarser)
Validates against the NDG reference on the real crop (side-by-side + sigma/autocorr metrics)."""
import os, numpy as np, io
from PIL import Image, ImageDraw
F=os.environ.get('NEX3N_PHOTOS','fixtures')   # test frames / fixtures dir

# --- measured sigma(V) from the ramp (ultramax400/0.15) ---
MV = np.array([8,24,40,56,72,88,104,120,135,152,168,184,200,216,232,248])
SY = np.array([0.19,1.52,3.37,5.27,6.98,8.29,8.79,8.74,8.06,6.90,5.50,3.79,2.24,1.15,0.39,0.00])
SCB= np.array([0.02,0.79,2.35,3.45,4.32,4.87,5.11,5.16,4.41,3.72,2.60,1.85,1.19,0.62,0.13,0.00])
SCR= np.array([0.02,0.46,1.21,2.08,2.60,3.01,3.06,2.95,2.79,2.24,1.63,1.36,0.47,0.48,0.11,0.00])
def lut(sv):
    x=np.arange(256); y=np.interp(x,MV,sv,left=0,right=0)
    y[:8]=np.interp(np.arange(8),[0,8],[0,sv[0]]); return np.clip(y,0,None).astype(np.float32)
LY,LCB,LCR=lut(SY),lut(SCB),lut(SCR)

# --- fit a separable blur kernel to the target luma autocorr ---
TARGET=np.array([1.0,0.82,0.47,0.20,0.07,0.01])
def kern_ac(k):
    a=np.correlate(k,k,'full'); a=a[len(a)//2:]; a=a/a[0]; return a[:6]
best=None
for s in np.linspace(0.6,2.0,60):
    i=np.arange(-4,5); k=np.exp(-0.5*(i/s)**2); e=np.sum((kern_ac(k)-TARGET)**2)
    if best is None or e<best[0]: best=(e,s,k)
_,s_best,kf=best
print('fit gaussian sigma=%.2f  autocorr=%s'%(s_best,np.round(kern_ac(kf),2)))
# integer kernel for the C port
ki=np.round(kf/kf.max()*16).astype(int); ki=ki[ki>0]
print('integer kernel (norm/16):',ki.tolist(),' autocorr=',np.round(kern_ac(ki.astype(float)),2))

def _conv1d(n,k,axis):
    k=k/k.sum(); c=len(k)//2; out=np.zeros_like(n)
    for j,w in enumerate(k):
        out=out+w*np.roll(n,j-c,axis=axis)
    return out
def blur_sep(n,k):
    return _conv1d(_conv1d(n,k,0),k,1)

def composite(rgb,seed=7,chroma_blur_extra=2.0):
    ycc=np.asarray(Image.fromarray(rgb).convert('YCbCr'),np.float32)
    Y=ycc[:,:,0]; H,W=Y.shape; rng=np.random.default_rng(seed)
    n=rng.standard_normal((H,W)).astype(np.float32)
    nb=blur_sep(n,kf); nb/=nb.std()+1e-6                    # unit-variance correlated luma grain
    ck=np.exp(-0.5*(np.arange(-7,8)/(s_best*chroma_blur_extra))**2)   # coarser chroma kernel
    ncb=blur_sep(rng.standard_normal((H,W)).astype(np.float32),ck); ncb/=ncb.std()+1e-6  # INDEPENDENT Cb
    ncr=blur_sep(rng.standard_normal((H,W)).astype(np.float32),ck); ncr/=ncr.std()+1e-6  # INDEPENDENT Cr
    Yi=np.clip(Y,0,255).astype(int)
    out=ycc.copy()
    out[:,:,0]=np.clip(Y + LY[Yi]*nb,0,255)
    out[:,:,1]=np.clip(ycc[:,:,1] + LCB[Yi]*ncb,0,255)
    out[:,:,2]=np.clip(ycc[:,:,2] + LCR[Yi]*ncr,0,255)
    rgb2=np.asarray(Image.fromarray(out.astype(np.uint8),'YCbCr').convert('RGB'))
    b=io.BytesIO(); Image.fromarray(rgb2).save(b,'JPEG',quality=95); b.seek(0)
    return np.asarray(Image.open(b).convert('RGB'))

# apply to the real crop and compare to the NDG ultramax reference
crop=np.asarray(Image.open(F+'/crop.jpg').convert('RGB'))
mine=composite(crop)
ref =np.asarray(Image.open(F+'/fg_ultra/crop_grain.jpg').convert('RGB'))
Image.fromarray(mine).save(F+'/_mine_ultra.png')

# metrics on a flat grey region (full-res coords within the 1000x1000 crop): approx dark grey
def sigY_region(a,b,y0,x0,s=200):
    ay=np.asarray(Image.fromarray(a[y0:y0+s,x0:x0+s]).convert('YCbCr'),np.float32)[:,:,0]
    by=np.asarray(Image.fromarray(b[y0:y0+s,x0:x0+s]).convert('YCbCr'),np.float32)[:,:,0]
    return float(ay.mean()),float((by-ay).std() if ay.shape==by.shape else -1)

# 3-panel 1:1 compare: clean | mine | NDG ref
box=(300,300,760,760)
tiles=[('CLEAN',crop),('MINE (fast composite)',mine),('NDG ultramax (ref)',ref)]
ct=[(n,Image.fromarray(t).crop(box)) for n,t in tiles]
W,Hh=ct[0][1].size; bar=20
cmp=Image.new('RGB',(W*3+12,Hh+bar),(25,25,25)); d=ImageDraw.Draw(cmp)
for i,(n,t) in enumerate(ct):
    x=i*(W+6); cmp.paste(t,(x,bar)); d.text((x+4,3),n,fill=(255,255,0))
cmp.save(F+'/_cmp_match.png'); print('saved _cmp_match.png',cmp.size)
# sigma match on a grey patch (the dark desk ~ top-left of crop)
gm,gs_mine=sigY_region(crop,mine,120,120); _,gs_ref=sigY_region(crop,ref,120,120)
print('grey patch meanY=%.0f  sigY mine=%.2f  NDG ref=%.2f'%(gm,gs_mine,gs_ref))
