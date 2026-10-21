"""Bake the grain tile + GAIN LUTs for the baked-tile shim. Deterministic -> regenerates grain_tile.bin +
grain_luts.h. Tile = 512x512 toroidal [1,4,1] blurred hash-noise (the LOCKED ultramax400 retune spectrum),
normalized to int8 (std ~50). GAIN_* = locked sigma (luma x0.60, soft chroma) * 256 / tile_std. Writes
grain_tile.bin + grain_luts.h into the current directory."""
import numpy as np
TILE=512; TSCALE=50
# Grain amplitude. 1.0 = sigma_Y ~3.5, matched to real UltraMax 400 scans and the look proven on the camera.
# 1.5 = sigma_Y ~5, the more visible build (validated offline only). Regenerate grain_luts.h after changing it.
STRENGTH=1.0
K=np.array([1,4,1]); KSUM=6
def hashn(H,W,s):
    xx=np.arange(W,dtype=np.uint64)[None,:]; yy=np.arange(H,dtype=np.uint64)[:,None]
    u=(xx*np.uint64(0x9E3779B1))^(yy*np.uint64(0x85EBCA77))^(np.uint64(s)*np.uint64(0xC2B2AE3D)); u&=np.uint64(0xFFFFFFFF)
    u^=u>>np.uint64(15); u=(u*np.uint64(0x2C1B3C6D))&np.uint64(0xFFFFFFFF); u^=u>>np.uint64(12)
    u=(u*np.uint64(0x297A2D39))&np.uint64(0xFFFFFFFF); u^=u>>np.uint64(15)
    return ((u&np.uint64(0xFF)).astype(np.int32))-128
def bpass(n,ax):
    acc=np.zeros_like(n,np.int32); c=len(K)//2
    for j,w in enumerate(K): acc+=w*np.roll(n,j-c,ax)   # toroidal (wrap) -> seamless tiling
    return (acc+KSUM//2)//KSUM
n=bpass(bpass(hashn(TILE,TILE,12345),0),1)
f=n.astype(np.float32); f=f/f.std()*TSCALE
tile=np.clip(np.round(f),-127,127).astype(np.int8); tile_std=float(tile.astype(np.float32).std())
tile.tofile('grain_tile.bin')
MV=np.array([8,24,40,56,72,88,104,120,135,152,168,184,200,216,232,248])
SY =np.array([0.19,1.52,3.37,5.27,6.98,8.29,8.79,8.74,8.06,6.90,5.50,3.79,2.24,1.15,0.39,0.00])*0.60*STRENGTH
SCB=np.array([0.02,0.79,2.35,3.45,4.32,4.87,5.11,5.16,4.41,3.72,2.60,1.85,1.19,0.62,0.13,0.00])*0.60*STRENGTH*0.38*0.38
SCR=np.array([0.02,0.46,1.21,2.08,2.60,3.01,3.06,2.95,2.79,2.24,1.63,1.36,0.47,0.48,0.11,0.00])*0.60*STRENGTH*0.38*0.38
def slut(sv):
    x=np.arange(256); y=np.interp(x,MV,sv,left=0,right=0); y[:8]=np.interp(np.arange(8),[0,8],[0,sv[0]]); return np.clip(y,0,None)
SHIFT=8
def gain(sv): return np.round(slut(sv)*(2**SHIFT)/tile_std).astype(int)
def emit(f,name,a):
    f.write('static const short %s[256]={\n'%name)
    for i in range(0,256,16): f.write('  '+','.join('%d'%v for v in a[i:i+16])+',\n')
    f.write('};\n')
with open('grain_luts.h','w') as f:
    f.write('/* BAKED-TILE retune ultramax400: 512^2 toroidal [1,4,1] tile, tile_std=%.1f, SHIFT=%d */\n'%(tile_std,SHIFT))
    f.write('#define GRAIN_TILE 512\n#define GRAIN_TMASK 511\n')
    emit(f,'GAIN_Y',gain(SY)); emit(f,'GAIN_CB',gain(SCB)); emit(f,'GAIN_CR',gain(SCR))
print('baked grain_tile.bin (std %.1f) + grain_luts.h'%tile_std)
