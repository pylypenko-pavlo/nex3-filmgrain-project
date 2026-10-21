"""Chart patch extraction (24 ColorChecker-like + 21-step gray wedge, target/layout.json)
from a camera JPEG and from the matching ARW (camera RGB), cached in cache/pairs.npz."""
import os, sys, json, glob, numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'measure'))
from patches import patches  # noqa: E402  (existing detector)
import rawio  # noqa: E402

LAY = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'measurements', 'chart_layout.json')))
TDIR = os.environ.get('NEX3N_CHARTS', 'charts') + '/'
CACHE = os.path.join(os.path.dirname(__file__), 'cache')

def _geom(img8):
    """Patch centres (full-res y,x) of the 24 cc patches + affine layout->image."""
    tmp = os.path.join(CACHE, '_det.png'); Image.fromarray(img8).save(tmp)
    c, _ = patches(tmp)
    ys = np.array([x[0] + x[2] / 2 for x in c]); xs = np.array([x[1] + x[3] / 2 for x in c])
    ph = np.median([x[2] for x in c])
    def clus(v):
        v = np.sort(v); cs = [[v[0]]]
        for a in v[1:]:
            (cs[-1].append(a) if a - cs[-1][-1] < ph * 0.5 else cs.append([a]))
        cs = sorted(cs, key=len, reverse=True)
        return sorted(np.mean(x) for x in cs[:{4: 4, 6: 6}[4]])
    rows = clus(ys)
    cs = np.sort(xs); cl = [[cs[0]]]
    for a in cs[1:]:
        (cl[-1].append(a) if a - cl[-1][-1] < ph * 0.5 else cl.append([a]))
    cols = sorted(np.mean(x) for x in sorted(cl, key=len, reverse=True)[:6])
    ic = np.array([(r * 4, cc * 4) for r in rows for cc in cols])
    lc = np.array([((a[1] + a[3]) / 2, (a[0] + a[2]) / 2) for a in LAY['cc']])
    X = np.c_[lc, np.ones(len(lc))]
    Ay = np.linalg.lstsq(X, ic[:, 0], rcond=None)[0]; Ax = np.linalg.lstsq(X, ic[:, 1], rcond=None)[0]
    return Ay, Ax

def _sample(img, Ay, Ax, frac=0.25, stat=np.median):
    out = []
    for box in LAY['cc'] + LAY['gray']:
        x0, y0, x1, y1 = box[:4]
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2; hh, hw = (y1 - y0) * frac, (x1 - x0) * frac
        y = Ay @ [cy, cx, 1]; x = Ax @ [cy, cx, 1]
        sy, sx = hh * abs(Ay[0]), hw * abs(Ax[1])
        out.append(stat(img[int(y - sy):int(y + sy), int(x - sx):int(x + sx)].reshape(-1, 3), 0))
    return np.array(out)

def extract(n):
    jp = TDIR + 'DSC%05d.JPG' % n; ar = TDIR + 'DSC%05d.ARW' % n
    jpg = np.asarray(Image.open(jp).convert('RGB'))
    Ay, Ax = _geom(jpg)
    J = _sample(jpg.astype(float), Ay, Ax)
    m = rawio.meta(ar); cam = rawio.load_cam(ar)
    wb = np.array(m['WB_RGGBLevels'])[[0, 1, 3]] / 1024.0
    M = np.array(m['ColorMatrix']).reshape(3, 3) / 1024.0
    # register raw half-res to JPEG/2: global shift + per-patch local refine (lens distortion correction in JPEG)
    jl = jpg.mean(-1); jl = jl[:jl.shape[0] // 2 * 2, :jl.shape[1] // 2 * 2]
    j2 = jl.reshape(jl.shape[0] // 2, 2, jl.shape[1] // 2, 2).mean((1, 3))
    rl = (cam.mean(-1) * 4).clip(0, 1) ** (1 / 2.2) * 255
    R = []
    for box in LAY['cc'] + LAY['gray']:
        x0, y0, x1, y1 = box[:4]
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        y = (Ay @ [cy, cx, 1]) / 2; x = (Ax @ [cy, cx, 1]) / 2
        hy = (y1 - y0) * abs(Ay[0]) / 4; hx = (x1 - x0) * abs(Ax[1]) / 4   # half-size in j2 px
        Y0, Y1, X0, X1 = int(y - hy * 1.2), int(y + hy * 1.2), int(x - hx * 1.2), int(x + hx * 1.2)
        b = j2[Y0:Y1, X0:X1]; best = (-2, 0, 0)
        for dy in range(-4, 11):
            for dx in range(-8, 11):
                a = rl[Y0 + dy:Y1 + dy, X0 + dx:X1 + dx]
                if a.shape != b.shape or a.std() < 1e-3 or b.std() < 1e-3: continue
                c = np.corrcoef(a.ravel(), b.ravel())[0, 1]
                if c > best[0]: best = (c, dy, dx)
        _, dy, dx = best if best[0] > 0.5 else (0, 3, 2)
        sy, sx = hy * 0.5, hx * 0.5
        R.append(cam[int(y + dy - sy):int(y + dy + sy), int(x + dx - sx):int(x + dx + sx)].reshape(-1, 3).mean(0))
    R = np.array(R)
    return dict(n=n, jpg=J, cam=R, wb=wb, M=M, meta=m)

if __name__ == '__main__':
    os.makedirs(CACHE, exist_ok=True)
    res = {}
    for p in sorted(glob.glob(TDIR + '*.ARW')):
        n = int(os.path.basename(p)[3:8])
        d = extract(n); res[n] = d
        m = d['meta']
        print(n, m['CreativeStyle'], 'sat', m.get('Saturation'), 'con', m.get('Contrast'),
              'gray J', np.round(d['jpg'][24:, 1][::4]).astype(int), 'cam G', np.round(d['cam'][24:, 1][::4] * 1000).astype(int))
    np.save(os.path.join(CACHE, 'pairs.npy'), res, allow_pickle=True)


def jpg_patches(path):
    jpg = np.asarray(Image.open(path).convert('RGB'))
    Ay, Ax = _geom(jpg)
    return _sample(jpg.astype(float), Ay, Ax)


def all_jpgs():
    """45 patches (24 cc + 21 gray) for every chart JPEG in tagret/ -> cache/jpg_patches.npy"""
    res = {}
    for p in sorted(glob.glob(TDIR + '*.JPG')):
        n = int(os.path.basename(p)[3:8])
        try:
            res[n] = dict(jpg=jpg_patches(p), meta=rawio.meta(p))
        except Exception as e:  # noqa: BLE001  (detector failure on odd frames: report and skip)
            print('skip', n, e)
    np.save(os.path.join(CACHE, 'jpg_patches.npy'), res, allow_pickle=True)
    return res
