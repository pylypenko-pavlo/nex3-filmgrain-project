"""Validation report for the simulator.

1. RAW+JPEG chart pairs (absolute): cache/fit_report.txt from fit_final.py (train/test split in fit.py).
2. JPEG cross-style prediction on chart sessions (hold-out: never used in the fit):
   Standard frame -> invert -> render other style with the session's block -> compare with the real frame (patches).
3. Same on real-world frames (live/): whole image at 1/8 size, pixels not clipped; median/mean dE76.
Null = 'the target looks like the source frame' (no change predicted).
"""
import glob
import os
import sys

import numpy as np
from PIL import Image

import block
import pipeline as pl
import rawio
from model import de76, srgb2lab

HERE = os.path.dirname(os.path.abspath(__file__))
PIC = os.environ.get('NEX3N_PHOTOS', 'photos') + '/'
J = np.load(os.path.join(HERE, 'cache', 'jpg_patches.npy'), allow_pickle=True).item()
for _n in J:  # refresh EXIF (WB levels)
    J[_n]['meta'] = rawio.meta(PIC + 'tagret/DSC%05d.JPG' % _n)

CHART_SESSIONS = [  # (source Standard frame, targets, block)
    (9440, [9441, 9442, 9443, 9444], 'looks_v1'),
    (9483, [9484, 9485, 9486, 9487], 'looks_v3'),
    (9498, [9499, 9500, 9501, 9502], 'looks_v5'),
    (9473, [9475, 9477], 'binary'),
    (9493, [9494, 9495, 9496, 9497], 'looks_v4'),
]
LIVE = [  # (source, targets, block)
    ('live/DSC09445.JPG', ['live/DSC09446.JPG', 'live/DSC09447.JPG', 'live/DSC09448.JPG', 'live/DSC09449.JPG'], 'looks_v1'),
    ('live/DSC09451.JPG', ['live/DSC09452.JPG', 'live/DSC09453.JPG', 'live/DSC09454.JPG', 'live/DSC09455.JPG'], 'looks_v1'),
    ('live/v5/DSC09505.JPG', ['live/v5/DSC09506.JPG', 'live/v5/DSC09507.JPG', 'live/v5/DSC09504.JPG'], 'looks_v5'),
]


def spec(meta, blk):
    # JPEG EXIF has no applied WB gains (Sony WB_RGBLevels = AWB estimate, not applied): same WB assumed
    return dict(block=blk, style=meta['CreativeStyle'].lower(), contrast=meta['Contrast'], sat=meta['Saturation'], wb=np.ones(3))


def ev(meta):
    return np.log2(meta['FNumber'] ** 2 / meta['ExposureTime'])


def rerender_exp(rgb, pp, src, dst, dev):
    """rerender with an exposure change of dev stops (linear scaling of camera RGB)."""
    ss = block.STYLE_SLOT[src['style']]; ds = block.STYLE_SLOT[dst['style']]
    y = pl.inverse_lin(rgb, pp, src['style'], block.table(src['block'], ss), src['contrast'], src['sat'])
    x = y @ np.linalg.inv(block.matrix(src['block'], ss) / 1024).T * 2.0 ** dev
    x = x / src['wb'] * dst['wb']
    out = pl.forward_lin(x @ (block.matrix(dst['block'], ds) / 1024).T, pp, dst['style'], block.table(dst['block'], ds),
                         dst['contrast'], dst['sat'])
    return np.round(out).astype(np.uint8)


def chart_part(pp, out):
    print('\n## JPEG cross-style on chart (patches, hold-out)', file=out)
    print('| source -> target | style | dE colour (model) | dE colour (null) | dE gray (model) |', file=out)
    print('|---|---|---|---|---|', file=out)
    res = []
    for s, ts, bk in CHART_SESSIONS:
        blk = block.load('00030001_%s.hex' % bk)
        src = spec(J[s]['meta'], blk)
        for t in ts:
            dst = spec(J[t]['meta'], blk)
            a, b = J[s]['jpg'], J[t]['jpg']
            pred = rerender_exp(a[None], pp, src, dst, 0.0)[0].astype(float)
            m = (a.max(1) < 250) & (b.max(1) < 250) & (a.min(1) > 2) & (b.min(1) > 2)
            d, d0 = de76(pred, b), de76(a, b)
            c = m.copy(); c[18:] = False; g = m.copy(); g[:24] = False
            res.append((d[c].mean(), d0[c].mean()))
            print('| %d -> %d (%s) | %s | %.2f | %.2f | %.2f |' % (s, t, bk, dst['style'], d[c].mean(), d0[c].mean(), d[g].mean()), file=out)
    r = np.array(res)
    print('\nmean colour dE: model %.2f, null %.2f' % tuple(r.mean(0)), file=out)


def load_small(p, k=8):
    im = Image.open(p).convert('RGB')
    return np.asarray(im.resize((im.width // k, im.height // k), Image.BOX)).astype(float)


def align(a, p, b, r=40):
    """shift a (and p) onto b; return 1/4-downsampled (i.e. 1/32 of full) overlapping crops."""
    la, lb = a.mean(-1), b.mean(-1)
    h, w = la.shape; best = (-2, 0, 0)
    for dy in range(-r, r + 1, 2):
        for dx in range(-r, r + 1, 2):
            A = la[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)]
            B = lb[max(0, -dy):h + min(0, -dy), max(0, -dx):w + min(0, -dx)]
            c = np.corrcoef(A[::3, ::3].ravel(), B[::3, ::3].ravel())[0, 1]
            if c > best[0]: best = (c, dy, dx)
    _, dy, dx = best
    for ddy in (-1, 0, 1):
        for ddx in (-1, 0, 1):
            y, x = dy + ddy, dx + ddx
            A = la[max(0, y):h + min(0, y), max(0, x):w + min(0, x)]
            B = lb[max(0, -y):h + min(0, -y), max(0, -x):w + min(0, -x)]
            c = np.corrcoef(A.ravel(), B.ravel())[0, 1]
            if c > best[0]: best = (c, y, x)
    corr, dy, dx = best
    cut = lambda im, y, x: im[max(0, y):h + min(0, y), max(0, x):w + min(0, x)]
    A, P, B = cut(a, dy, dx), cut(p, dy, dx), cut(b, -dy, -dx)
    def ds(im, k=4):
        hh, ww = im.shape[0] // k * k, im.shape[1] // k * k
        return im[:hh, :ww].reshape(hh // k, k, ww // k, k, 3).mean((1, 3))
    return ds(A), ds(P), ds(B), corr


SECT = [(330, 30, 'red'), (30, 70, 'skin/orange'), (70, 105, 'yellow'), (105, 165, 'green'), (165, 235, 'cyan'),
        (235, 300, 'blue'), (300, 330, 'violet')]


def stats(rgb, m):
    """framing-robust statistics: L p5/p50/p95; per hue sector (C*>12): pixel share, mean C*, circular mean h."""
    lab = srgb2lab(rgb)[m]
    L = lab[:, 0]; C = np.hypot(lab[:, 1], lab[:, 2]); h = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
    out = {'L': np.percentile(L, [5, 50, 95])}
    for a, b, name in SECT:
        sel = (C > 12) & (((h >= a) & (h < b)) if a < b else ((h >= a) | (h < b)))
        if sel.sum() == 0:
            out[name] = (0.0, np.nan, np.nan); continue
        hm = np.degrees(np.angle(np.exp(1j * np.radians(h[sel])).mean())) % 360
        out[name] = (sel.mean(), C[sel].mean(), hm)
    return out


def stat_err(p, b):
    """mean |dC| and |dh| over sectors holding >=3 % of pixels in the target; |dL| over percentiles."""
    dC, dh = [], []
    for _, _, name in SECT:
        if b[name][0] < 0.03 or np.isnan(p[name][1]):
            continue
        dC.append(abs(p[name][1] - b[name][1])); dh.append(abs((p[name][2] - b[name][2] + 180) % 360 - 180))
    return np.mean(np.abs(p['L'] - b['L'])), np.mean(dC), np.mean(dh)


def live_part(pp, out):
    print('\n## JPEG cross-style on real frames (hold-out; frames are re-framed handheld, pixels after shift registration + framing-robust hue-sector statistics)', file=out)
    print('| source -> target | style | dEV | registration r | median dE pixels model / null | |dC| sectors model / null | |dh| sectors model / null |', file=out)
    print('|---|---|---|---|---|---|---|', file=out)
    acc = []
    for s, ts, bk in LIVE:
        blk = block.load('00030001_%s.hex' % bk)
        ms = rawio.meta(PIC + s); a = load_small(PIC + s)
        src = spec(ms, blk)
        for t in ts:
            mt = rawio.meta(PIC + t); b = load_small(PIC + t)
            dst = spec(mt, blk)
            dev = ev(ms) - ev(mt)
            pred = rerender_exp(a, pp, src, dst, dev).astype(float)
            ma = (a.max(-1) < 250) & (a.min(-1) > 3); mb = (b.max(-1) < 250) & (b.min(-1) > 3)
            sp, sa, sb = stats(pred, ma), stats(a, ma), stats(b, mb)
            em, e0 = stat_err(sp, sb), stat_err(sa, sb)
            acc.append(em + e0)
            a2, p2, b2, corr = align(a, pred, b)
            m = (a2.max(-1) < 245) & (b2.max(-1) < 245) & (a2.min(-1) > 4) & (b2.min(-1) > 4)
            dpx, dpx0 = np.median(de76(p2, b2)[m]), np.median(de76(a2, b2)[m])
            print('| %s -> %s | %s | %+.2f | %.3f | %.1f / %.1f | %.1f / %.1f | %.1f / %.1f |' % (
                os.path.basename(s), os.path.basename(t), dst['style'], dev, corr, dpx, dpx0, em[1], e0[1], em[2], e0[2]), file=out)
    r = np.array(acc).mean(0)
    print('\nmean over pairs: |dC| %.1f / %.1f, |dh| %.1f / %.1f (model / null)' % (r[1], r[4], r[2], r[5]), file=out)


if __name__ == '__main__':
    pp = pl.load_params()
    out = sys.stdout
    chart_part(pp, out)
    live_part(pp, out)
