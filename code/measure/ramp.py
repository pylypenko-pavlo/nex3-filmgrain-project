import sys,os,json,numpy as np,subprocess
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from patches import patches,srgb2lab
from PIL import Image
LAY=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","data","measurements","chart_layout.json")))
T=os.environ.get("NEX3N_CHARTS","charts")+"/"
def centers(path):
    c,small=patches(path)
    ys=np.array([x[0]+x[2]/2 for x in c]); xs=np.array([x[1]+x[3]/2 for x in c])
    ph=np.median([x[2] for x in c])
    def clus(v):
        v=np.sort(v); cs=[[v[0]]]
        for a in v[1:]: (cs[-1].append(a) if a-cs[-1][-1]<ph*0.5 else cs.append([a]))
        return [np.mean(x) for x in cs]
    rows=clus(ys); cols=clus(xs)
    return [(r*4,cc*4) for r in rows for cc in cols]
def ramp(n):
    p=T+"DSC%05d.JPG"%n
    im=np.asarray(Image.open(p).convert('RGB')).astype(float)
    ic=np.array(centers(p))  # (y,x) image
    lc=np.array([((a[1]+a[3])/2,(a[0]+a[2])/2) for a in LAY["cc"]])  # (y,x) layout
    X=np.c_[lc,np.ones(len(lc))]; Ay=np.linalg.lstsq(X,ic[:,0],rcond=None)[0]; Ax=np.linalg.lstsq(X,ic[:,1],rcond=None)[0]
    out=[]
    for g in LAY["gray"]:
        cy=(g[1]+g[3])/2; cx=(g[0]+g[2])/2; hh=(g[3]-g[1])*0.25; hw=(g[2]-g[0])*0.25
        y=Ay@[cy,cx,1]; x=Ax@[cy,cx,1]; sy=hh*abs(Ay[0]); sx=hw*abs(Ax[1])
        out.append(im[int(y-sy):int(y+sy),int(x-sx):int(x+sx)].reshape(-1,3).mean(0))
    rgb=np.array(out); return [g[4] for g in LAY["gray"]], rgb, srgb2lab(rgb)
if __name__=="__main__":
    res={}
    for n in map(int,sys.argv[1:]):
        ex=json.loads(subprocess.run(['exiftool','-j','-CreativeStyle','-Contrast','-ExposureTime','-WhiteBalance',T+"DSC%05d.JPG"%n],capture_output=True,text=True).stdout)[0]
        x,rgb,lab=ramp(n); res[n]=(x,rgb.tolist())
        print(n,ex.get("CreativeStyle"),"c=",ex.get("Contrast"),ex.get("ExposureTime"),"Y':"," ".join("%3d"%v for v in rgb.mean(1)))
    json.dump(res,open(os.path.join(os.path.dirname(__file__),"ramps.json"),"w"))
