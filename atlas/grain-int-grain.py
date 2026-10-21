"""Integer-exact grain (what the C shim will do), validated vs the locked look.
All per-pixel math is integer (uint8 planes, int32 intermediates, fixed-point sigma LUT, separable int blur
with kernel [1,4,11,16,11,4,1]/48). Proves the C port reproduces the ultramax look before transcription."""
import os, numpy as np, io
from PIL import Image, ImageDraw
F=os.environ.get('NEX3N_PHOTOS','fixtures')   # test frames / fixtures dir
K=np.array([1,4,11,16,11,4,1],np.int32); KSUM=48
MV=np.array([8,24,40,56,72,88,104,120,135,152,168,184,200,216,232,248])
SY=np.array([0.19,1.52,3.37,5.27,6.98,8.29,8.79,8.74,8.06,6.90,5.50,3.79,2.24,1.15,0.39,0.00])
SCB=np.array([0.02,0.79,2.35,3.45,4.32,4.87,5.11,5.16,4.41,3.72,2.60,1.85,1.19,0.62,0.13,0.00])
SCR=np.array([0.02,0.46,1.21,2.08,2.60,3.01,3.06,2.95,2.79,2.24,1.63,1.36,0.47,0.48,0.11,0.00])
def sigma_lut(sv):
    x=np.arange(256); y=np.interp(x,MV,sv,left=0,right=0); y[:8]=np.interp(np.arange(8),[0,8],[0,sv[0]]); return np.clip(y,0,None)

SHIFT=8
# blurred unit-ish noise std for calibration: uniform[-128,127] std ~73.9, each separable pass scales std by
# sqrt(sum((K/KSUM)^2)); measured empirically below and folded into the LUT scale.
def hash_noise(H,W,seed):
    xx=np.arange(W,dtype=np.uint64)[None,:]; yy=np.arange(H,dtype=np.uint64)[:,None]
    u=(xx*np.uint64(0x9E3779B1)) ^ (yy*np.uint64(0x85EBCA77)) ^ (np.uint64(seed)*np.uint64(0xC2B2AE3D))
    u=u & np.uint64(0xFFFFFFFF)
    u^=u>>np.uint64(15); u=(u*np.uint64(0x2C1B3C6D))&np.uint64(0xFFFFFFFF)
    u^=u>>np.uint64(12); u=(u*np.uint64(0x297A2D39))&np.uint64(0xFFFFFFFF); u^=u>>np.uint64(15)
    return ((u & np.uint64(0xFF)).astype(np.int32))-128   # [-128,127]
def blur_pass(n,axis):
    acc=np.zeros_like(n,np.int32)
    for j,w in enumerate(K): acc+= w*np.roll(n,j-3,axis=axis)
    return (acc + KSUM//2)//KSUM
def blur2d(n,passes=1):
    for _ in range(passes): n=blur_pass(blur_pass(n,0),1)
    return n

def grain_plane(plane_u8, Yfull, seed, Lsig, blur_passes, cal):
    H,W=plane_u8.shape
    n=hash_noise(H,W,seed); b=blur2d(n,blur_passes)
    # fixed-point gain per source tone (sample Y at this plane's resolution)
    Yi=Yfull if Yfull.shape==plane_u8.shape else np.asarray(Image.fromarray(Yfull).resize((W,H),Image.BILINEAR))
    gainLUT=np.round(Lsig*(2**SHIFT)/cal).astype(np.int32)         # scaleLUT[V]
    g=(b*gainLUT[np.clip(Yi,0,255)]) >> SHIFT
    return np.clip(plane_u8.astype(np.int32)+g,0,255).astype(np.uint8)

def composite_int(rgb,seed=7):
    ycc=np.asarray(Image.fromarray(rgb).convert('YCbCr'))
    Y=ycc[:,:,0].copy()
    # calibrate blur std once (per passes) so sigma LUT maps to real luma std
    cal_l=blur2d(hash_noise(256,256,99),1).std()
    cal_c=blur2d(hash_noise(256,256,99),2).std()
    out=ycc.copy()
    out[:,:,0]=grain_plane(Y,Y,seed,  sigma_lut(SY), 1, cal_l)
    out[:,:,1]=grain_plane(ycc[:,:,1],Y,seed+101,sigma_lut(SCB),2,cal_c)
    out[:,:,2]=grain_plane(ycc[:,:,2],Y,seed+202,sigma_lut(SCR),2,cal_c)
    rgb2=np.asarray(Image.fromarray(out,'YCbCr').convert('RGB'))
    bio=io.BytesIO(); Image.fromarray(rgb2).save(bio,'JPEG',quality=95); bio.seek(0)
    return np.asarray(Image.open(bio).convert('RGB'))

crop=np.asarray(Image.open(F+'/crop.jpg').convert('RGB'))
mine=composite_int(crop)
ref=np.asarray(Image.open(F+'/fg_ultra/crop_grain.jpg').convert('RGB'))
Image.fromarray(mine).save(F+'/_mine_int.png')
def sigY(a,b,y0=120,x0=120,s=200):
    ay=np.asarray(Image.fromarray(a[y0:y0+s,x0:x0+s]).convert('YCbCr'),np.float32)[:,:,0]
    by=np.asarray(Image.fromarray(b[y0:y0+s,x0:x0+s]).convert('YCbCr'),np.float32)[:,:,0]
    return float(ay.mean()),float((by-ay).std())
m,sm=sigY(crop,mine); _,sr=sigY(crop,ref)
print('INT grain  grey meanY=%.0f  sigY int=%.2f  NDG ref=%.2f'%(m,sm,sr))
box=(300,300,760,760)
tiles=[('CLEAN',crop),('INT composite (C-exact)',mine),('NDG ultramax ref',ref)]
ct=[(n,Image.fromarray(t).crop(box)) for n,t in tiles]; W,Hh=ct[0][1].size; bar=20
cmp=Image.new('RGB',(W*3+12,Hh+bar),(25,25,25)); d=ImageDraw.Draw(cmp)
for i,(n,t) in enumerate(ct):
    x=i*(W+6); cmp.paste(t,(x,bar)); d.text((x+4,3),n,fill=(255,255,0))
cmp.save(F+'/_cmp_int.png'); print('saved _cmp_int.png')
