import numpy as np, sys, os, subprocess, json
from PIL import Image
from patches import patches, srgb2lab
def grid(path):
    c,small=patches(path)
    ys=np.array([x[0]+x[2]/2 for x in c]); xs=np.array([x[1]+x[3]/2 for x in c])
    ph=np.median([x[2] for x in c]); pw=np.median([x[3] for x in c])
    # cluster rows/cols
    def clus(v,k):
        v=np.sort(v); cs=[[v[0]]]
        for a in v[1:]:
            (cs[-1].append(a) if a-cs[-1][-1]<ph*0.5 else cs.append([a]))
        return [np.mean(x) for x in cs]
    rows=clus(ys,4); cols=clus(xs,6)
    assert len(rows)==4 and len(cols)==6,(len(rows),len(cols))
    im=np.asarray(Image.open(path).convert('RGB')).astype(float)
    out=[]
    for r in rows:
        for cc in cols:
            y,x=int(r*4),int(cc*4); hh,ww=int(ph*4*0.25),int(pw*4*0.25)
            out.append(im[y-hh:y+hh,x-ww:x+ww].reshape(-1,3).mean(0))
    return np.array(out)
names=['dark skin','light skin','blue sky','foliage','blue flower','bluish green','orange','purplish blue','moderate red','purple','yellow green','orange yellow','blue','green','red','yellow','magenta','cyan','white','n8','n6.5','n5','n3.5','black']
if __name__=='__main__':
    res={}
    for p in sys.argv[1:]:
        ex=json.loads(subprocess.run(['exiftool','-j','-CreativeStyle','-Saturation','-Contrast',p],capture_output=True,text=True).stdout)[0]
        rgb=grid(p); lab=srgb2lab(rgb); C=np.hypot(lab[:,1],lab[:,2])
        key=os.path.basename(p)+' %s s=%s c=%s'%(ex['CreativeStyle'],ex['Saturation'],ex['Contrast'])
        res[key]=(rgb,lab,C)
        g=lab[18:24]
        print('%-40s chroma18=%.1f  grayL=%s  gray_ab=%s'%(key,C[:18].mean(),np.round(g[:,0]).astype(int),[(round(a),round(b)) for a,b in g[:,1:3]]))
    np.save('meas.npy',{k:v for k,v in res.items()},allow_pickle=True)
