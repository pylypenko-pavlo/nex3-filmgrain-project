"""Joint fit of the NEX-3N pipeline model.

Data
  RAW+JPEG pairs (tagret/DSC09417-09438, 04.10, original hue tables, various matrices/sliders/WB): absolute.
  JPEG-only table experiments (05.10): relative pairs base->target within a session, same matrices,
  only hue tables differ; gray wedge used to remove frame-to-frame drift.
Output: cache/params.npz  (+ printed validation)
"""
import os
import sys

import numpy as np
from scipy.optimize import least_squares

import block
import hue
import model

HERE = os.path.dirname(os.path.abspath(__file__))
P = np.load(os.path.join(HERE, 'cache', 'pairs.npy'), allow_pickle=True).item()
J = np.load(os.path.join(HERE, 'cache', 'jpg_patches.npy'), allow_pickle=True).item()
ORIG = block.orig()
B = {k: block.load('00030001_%s.hex' % k) for k in ('binary', 'bytes', 'bands', 'looks_v3', 'looks_v4', 'looks_v5', 'v3_e1')}
SLOT = {'Standard': 0, 'Vivid': 1, 'Portrait': 2, 'Landscape': 3, 'Sunset': 4}

RAW_TRAIN = [9419, 9420, 9421, 9422, 9423, 9424, 9431, 9434, 9417, 9418, 9432, 9435, 9437]
RAW_TEST = [9425, 9426, 9427, 9428, 9429, 9430, 9433, 9436, 9438]

# (target, base, block_target, block_base)
REL_TRAIN = [(9473, 9483, 'binary', 'looks_v3'), (9474, 9484, 'binary', 'looks_v3'), (9476, 9486, 'binary', 'looks_v3'),
             (9478, 9483, 'bytes', 'looks_v3'), (9479, 9484, 'bytes', 'looks_v3'), (9480, 9485, 'bytes', 'looks_v3'),
             (9481, 9486, 'bytes', 'looks_v3'),
             (9488, 9483, 'bands', 'looks_v3'), (9489, 9484, 'bands', 'looks_v3'), (9490, 9485, 'bands', 'looks_v3'),
             (9491, 9486, 'bands', 'looks_v3'),
             (9469, 9483, 'v3_e1', 'looks_v3')]
REL_TEST = [(9494, 9499, 'looks_v4', 'looks_v5'), (9495, 9500, 'looks_v4', 'looks_v5'), (9496, 9501, 'looks_v4', 'looks_v5'),
            (9497, 9502, 'looks_v4', 'looks_v5'),
            (9499, 9484, 'looks_v5', 'looks_v3'), (9500, 9485, 'looks_v5', 'looks_v3'), (9501, 9486, 'looks_v5', 'looks_v3'),
            (9502, 9487, 'looks_v5', 'looks_v3')]
# controls (same block both frames): pure noise/drift reference
REL_CTRL = [(9475, 9485, 'binary', 'looks_v3'), (9477, 9487, 'binary', 'looks_v3'), (9482, 9487, 'bytes', 'looks_v3'),
            (9492, 9487, 'bands', 'looks_v3'), (9493, 9498, 'looks_v4', 'looks_v5')]

PORTRAIT_CURVE = os.environ.get('PORTRAIT_CURVE', 'k1')  # hypothesis switch


def style_curve(style, contrast, portrait=None):
    """1024-entry curve = style curve o contrast curve (codes)."""
    T = model.TONE
    con = T[3 + contrast]
    s = style.lower()
    pc = portrait or PORTRAIT_CURVE
    if s in ('vivid', 'landscape', 'sunset'):
        st = T[14]
    elif s == 'portrait':
        st = T[int(pc[1:])]
    else:
        st = T[3]
    return np.interp(con, np.arange(1024), st)


NF = 26
NB = 4   # style boosts vivid, portrait, landscape, sunset (log)
IDX = {}
_o = 0
for name, n in (('F', NF), ('hue', hue.NP), ('boost', NB), ('satk', 1), ('H0', 18), ('C', 6), ('blk', 3), ('mg', 1), ('cp', 2)):
    IDX[name] = slice(_o, _o + n); _o += n
NPAR = _o
BOOST_I = {'Vivid': 0, 'Portrait': 1, 'Landscape': 2, 'Sunset': 3}


def x0():
    x = np.zeros(NPAR)
    x[IDX['hue']] = np.r_[np.deg2rad([105, 180, 285, 350]), np.full(4, -0.004), np.full(4, 0.004), [1, 0.5, 1, 0.5]]
    x[IDX['satk']] = 0.125
    return x


def params(x):
    h0 = x[IDX['H0']]
    return dict(F=x[IDX['F']], gain=1.0, hue=hue.unpack(x[IDX['hue']]), boost=x[IDX['boost']], satk=x[IDX['satk']][0],
                H0=dict(gain=h0[:9], rot=h0[9:]), C=cmat(x[IDX['C']]), blk=x[IDX['blk']] * 1e-3 * (os.environ.get('BLK', '0') == '1'),
                mg=np.exp(x[IDX['mg']][0]) if os.environ.get('MG', '0') == '1' else 1.0,
                cp=x[IDX['cp']] if os.environ.get('CP', '0') == '1' else np.zeros(2))


CPOS = os.environ.get('CPOS', 'none')  # hypothesis switch: extra fixed 3x3 'pre' (M@C@x) or 'post' (C@M@x) the slot matrix


def cmat(v):
    """3x3 with unit row sums (keeps neutrals) from 6 params."""
    C = np.eye(3)
    if CPOS == 'none':
        return C
    C[0, 1:] += v[0:2]; C[1, [0, 2]] += v[2:4]; C[2, :2] += v[4:6]
    C[np.arange(3), np.arange(3)] -= C.sum(1) - 1
    return C


def chroma_factor(pp, style, sat):
    b = np.exp(pp['boost'][BOOST_I[style]]) if style in BOOST_I else 1.0
    return b * (1 + pp['satk'] * sat)


HUE_POS = os.environ.get('HUE_POS', 'post')  # hypothesis switch: colour stages after ('post') or before ('pre') the tone curve


def colour_stage(e, pp, style, sat, T, flag='ignore'):
    ycc = model.rgb2ycc(e)
    ycc[..., 1:] *= chroma_factor(pp, style, sat)
    ycc = model.hue_stage(ycc, pp['H0'])
    if np.any(pp['cp']):  # chroma-magnitude nonlinearity: C -> C * (1 + a*t/(1+t)), t = C/c0 (hypothesis switch CP=1)
        C = np.hypot(ycc[..., 1], ycc[..., 2]); c0 = 60 * np.exp(pp['cp'][1])
        t = C / c0
        ycc[..., 1:] *= (1 + pp['cp'][0] * t / (1 + t))[..., None]
    ycc[..., 1:] = hue.apply(ycc[..., 1:], delta_table(T, flag), pp['hue'])
    return model.ycc2rgb(ycc)


def render_lin(y, pp, style, sat, contrast, T, flag='ignore', curve=None):
    """Post-matrix linear RGB -> JPEG sRGB 0..255 (full model)."""
    e = model.base_gamma(np.maximum(y * pp['gain'], 0), pp['F'])
    c = style_curve(style, contrast) if curve is None else curve
    if HUE_POS == 'pre':
        e = colour_stage(e, pp, style, sat, T, flag)
        e = np.interp(np.clip(e, 0, 1023), np.arange(1024), c)
    else:
        e = np.interp(np.clip(e, 0, 1023), np.arange(1024), c)
        e = colour_stage(e, pp, style, sat, T, flag)
    return np.clip(e, 0, 1023) * 255 / 1023


T_STD = block.table(ORIG, 0)


def delta_table(T, flag='ignore'):
    """Record minus the native Standard record. A quad of -128 (Sunset Q1 marker): 'zero' -> treated as 0,
    'ignore' -> treated as the Standard value, 'literal' -> -128."""
    T = np.array(T, float).copy()
    for q in range(6):
        if np.all(T[q] == -128):
            if flag == 'zero':
                T[q] = 0
            elif flag == 'ignore':
                T[q] = T_STD[q]
    return T - T_STD


def sim_raw(n, pp, flag='ignore'):
    d = P[n]; m = d['meta']; st = m['CreativeStyle']
    x = (d['cam'] - pp['blk']) * d['wb']
    g = pp['mg']
    xg = np.maximum(x, 0) ** (1 / g)
    y = (xg @ pp['C'].T) @ d['M'].T if CPOS == 'pre' else (xg @ d['M'].T) @ pp['C'].T
    y = np.sign(y) * np.abs(y) ** g
    T = block.table(ORIG, SLOT[st])
    return render_lin(y, pp, st, m['Saturation'], m['Contrast'], T, flag)


def drift_fix(base, target):
    """Per-channel monotone map from base gray wedge to target gray wedge (codes), applied to base."""
    gb, gt = base[24:], target[24:]
    out = base.copy()
    for c in range(3):
        o = np.argsort(gb[:, c]); xb = gb[o, c]; xt = np.maximum.accumulate(gt[o, c])
        out[:, c] = np.interp(base[:, c], xb, xt)
    return out


def table_swap(rgb, style, contrast, Tb, Tt, pp, flag='ignore'):
    """JPEG-domain edit: remove the hue-table effect of record Tb and apply record Tt (sRGB 0..255 in/out)."""
    e = rgb * 1023 / 255
    c = style_curve(style, contrast)
    if HUE_POS == 'pre':
        e = np.interp(e, c, np.arange(1024))
    ycc = model.rgb2ycc(e)
    ycc[..., 1:] = hue.apply(ycc[..., 1:], delta_table(Tb, flag), pp['hue'], inverse=True)
    ycc[..., 1:] = hue.apply(ycc[..., 1:], delta_table(Tt, flag), pp['hue'])
    e = model.ycc2rgb(ycc)
    if HUE_POS == 'pre':
        e = np.interp(np.clip(e, 0, 1023), np.arange(1024), c)
    return np.clip(e, 0, 1023) * 255 / 1023


def sim_rel(t, b, kt, kb, pp, flag='ignore', fix=True):
    m = J[t]['meta']; st = m['CreativeStyle']; slot = SLOT[st]
    base = J[b]['jpg'].astype(float)
    if fix:
        base = drift_fix(base, J[t]['jpg'].astype(float))
    return table_swap(base, st, m['Contrast'], block.table(B[kb], slot), block.table(B[kt], slot), pp, flag)


def okmask(*arrs):
    m = np.ones(len(arrs[0]), bool)
    for a in arrs:
        m &= (a.max(1) < 250) & (a.min(1) > 2)
    return m


def residuals(x, flag='ignore', w_rel=1.0):
    pp = params(x); r = []
    for n in RAW_TRAIN:
        Jt = P[n]['jpg']; S = sim_raw(n, pp, flag); m = okmask(Jt)
        r.append((model.srgb2lab(S) - model.srgb2lab(Jt))[m].ravel())
    for t, b, kt, kb in REL_TRAIN:
        Jt = J[t]['jpg']; S = sim_rel(t, b, kt, kb, pp, flag); m = okmask(Jt, J[b]['jpg'])
        r.append(w_rel * (model.srgb2lab(S) - model.srgb2lab(Jt))[m][:18].ravel())
    r.append(0.3 * x[IDX['F']])  # weak smoothness/regularisation of the gamma increments
    return np.concatenate(r)


def report(x, flag='ignore', out=sys.stdout):
    pp = params(x)
    rows = []
    def line(tag, n, de, m):
        c = de[:18][m[:18]]; g = de[24:][m[24:]]
        rows.append((tag, n, de[m].mean(), c.mean(), np.percentile(c, 90), g.mean()))
        print('%-10s %-24s dE76 all %5.2f | colour %5.2f (p90 %5.2f) | gray %5.2f' % rows[-1], file=out)
    for tag, lst in (('RAW-train', RAW_TRAIN), ('RAW-test', RAW_TEST)):
        for n in lst:
            Jt = P[n]['jpg']; S = sim_raw(n, pp, flag); m = okmask(Jt)
            line(tag, '%d %s s%+d c%+d' % (n, P[n]['meta']['CreativeStyle'], P[n]['meta']['Saturation'], P[n]['meta']['Contrast']), model.de76(S, Jt), m)
    for tag, lst in (('REL-train', REL_TRAIN), ('REL-test', REL_TEST), ('REL-ctrl', REL_CTRL)):
        for t, b, kt, kb in lst:
            Jt = J[t]['jpg']; S = sim_rel(t, b, kt, kb, pp, flag); m = okmask(Jt, J[b]['jpg'])
            S0 = drift_fix(J[b]['jpg'].astype(float), Jt.astype(float))  # 'no table change' prediction
            de, de0 = model.de76(S, Jt), model.de76(S0, Jt)
            line(tag, '%d<-%d %s' % (t, b, kt), de, m)
            print('%-10s %-24s   (null model: colour %5.2f)' % ('', '', de0[:18][m[:18]].mean()), file=out)
    return rows


if __name__ == '__main__':
    flag = os.environ.get('FLAG', 'ignore')
    x = x0()
    r = least_squares(residuals, x, args=(flag,), method='trf', max_nfev=400, verbose=0)
    x = r.x
    pp = params(x)
    print('flag', flag, 'portrait', PORTRAIT_CURVE, 'cost', r.cost)
    print('theta deg', np.round(np.rad2deg(pp['hue']['theta']) % 360, 1), 'alpha deg/unit', np.round(np.rad2deg(pp['hue']['alpha']), 3),
          'beta %/unit', np.round(100 * pp['hue']['beta'], 3), 'w2 w4 w3 w5', np.round(pp['hue']['w'], 2))
    print('boost (vivid, portrait, landscape, sunset)', np.round(np.exp(pp['boost']), 3), 'sat step', round(pp['satk'], 4))
    report(x, flag)
    np.savez(os.path.join(HERE, 'cache', 'params_%s_%s.npz' % (flag, PORTRAIT_CURVE)), x=x)
