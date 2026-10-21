import numpy as np, sys, os, json
from PIL import Image
from scipy import ndimage
def srgb2lab(rgb):
    c=rgb/255.0; c=np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
    M=np.array([[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]])
    xyz=c@M.T/np.array([0.95047,1.0,1.08883])
    f=np.where(xyz>0.008856,np.cbrt(xyz),7.787*xyz+16/116)
    return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)
def patches(path):
    im=np.asarray(Image.open(path).convert('RGB')).astype(float)
    small=im[::4,::4]; v=small.max(-1)
    mask=v>v.max()*0.0+45  # brighter than dark bg
    lab,n=ndimage.label(mask)
    objs=ndimage.find_objects(lab)
    cands=[]
    for i,sl in enumerate(objs):
        h=sl[0].stop-sl[0].start; w=sl[1].stop-sl[1].start
        area=(lab[sl]==i+1).sum()
        if 0.75<w/h<1.35 and area>0.8*w*h and w>40: cands.append((sl[0].start,sl[1].start,h,w))
    # take 24 largest-ish similar size squares
    cands.sort(key=lambda c:-c[2]*c[3]); med=np.median([c[2]*c[3] for c in cands[:18]])
    cands=[c for c in cands if 0.6*med<c[2]*c[3]<1.5*med]
    return cands, small
if __name__=='__main__':
    for p in sys.argv[1:]:
        c,_=patches(p); print(os.path.basename(p), len(c))
