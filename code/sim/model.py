"""NEX-3N JPEG colour/tone pipeline model (forward, numpy).

Stages (order as fitted on RAW+JPEG pairs, see fit.py / notes/simulator.md):
  cam (black-subtracted, /white)                       rawio.load_cam
  -> x = cam * WB gains (WB_RGGBLevels/1024)           as-shot or user
  -> y = M_slot @ x  (linear light, 1.0 = 1024)        block.matrix / EXIF ColorMatrix
  -> e = F(gain * y) per channel, 0..1023 code          base gamma, fitted (params['F'])
  -> e = T_k(e) per channel                             tone curve from av-cam (k3 = identity)
  -> YCbCr (BT.601 on codes), chroma *= S(style, sat)   style boost + Saturation slider
  -> hue/sat stage (native table baked into params['H']; delta vs native via hue.py)
  -> RGB 8 bit (JPEG)
"""
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TONE = np.load(os.path.join(HERE, 'cache', 'tone_k.npy')).astype(float)  # 21 x 1024, av-cam 0x5b006a+0x800k

# default curve index for each style at Contrast 0 (nex3n-tone-curve.md §0); contrast c -> k(3+c)
STYLE_CURVE = {'standard': 3, 'vivid': 14, 'landscape': 14, 'sunset': 14, 'portrait': 1}

LOGK = np.linspace(-11, 1.5, 26)  # knots of the base gamma in log2(linear)


def base_gamma(y, fp):
    """Monotone F: linear (>=0) -> code 0..1023. fp: 26 log-increments (softplus) of the knot values."""
    inc = np.log1p(np.exp(fp))
    vals = np.cumsum(inc)
    vals = vals / vals[-1] * 1023 * 1.0
    u = np.log2(np.maximum(y, 2.0 ** -16))
    out = np.interp(u, LOGK, vals)
    # linear toe below the first knot (through 0)
    toe = y / 2.0 ** LOGK[0] * vals[0]
    return np.where(u < LOGK[0], toe, out)


def tone(e, curve):
    """Apply a 1024-entry tone curve to codes 0..1023 (linear interpolation)."""
    c = TONE[curve] if np.isscalar(curve) else np.asarray(curve, float)
    return np.interp(np.clip(e, 0, 1023), np.arange(1024), c)


_K601 = np.array([[0.299, 0.587, 0.114], [-0.168736, -0.331264, 0.5], [0.5, -0.418688, -0.081312]])
_K601i = np.linalg.inv(_K601)


def rgb2ycc(rgb):
    return rgb @ _K601.T


def ycc2rgb(ycc):
    return ycc @ _K601i.T


def hue_stage(ycc, H):
    """Hue-dependent chroma gain / rotation in the CbCr plane.
    H: dict with 'gain' (Fourier coeffs, len 2n+1) and 'rot' (radians, Fourier coeffs) as functions of hue angle."""
    if H is None:
        return ycc
    cb, cr = ycc[..., 1], ycc[..., 2]
    h = np.arctan2(cr, cb)
    C = np.hypot(cb, cr)

    def four(c, h):
        c = np.asarray(c); n = (len(c) - 1) // 2
        v = c[0] * np.ones_like(h)
        for i in range(1, n + 1):
            v = v + c[2 * i - 1] * np.cos(i * h) + c[2 * i] * np.sin(i * h)
        return v
    g = np.exp(four(H['gain'], h))
    r = four(H['rot'], h)
    # soften at low chroma so neutrals stay neutral (codes 0..1023 scale)
    w = C / (C + H.get('c0', 8.0))
    g = 1 + (g - 1) * w
    r = r * w
    h2 = h + r
    C2 = C * g
    out = ycc.copy()
    out[..., 1] = C2 * np.cos(h2)
    out[..., 2] = C2 * np.sin(h2)
    return out


def forward_lin(y, p, curve=3, chroma=1.0, H=None, hue_delta=None):
    """Linear (post-matrix) RGB -> JPEG-like sRGB 0..255 float."""
    e = base_gamma(np.maximum(y * p['gain'], 0), p['F'])
    e = tone(e, curve)
    ycc = rgb2ycc(e)
    ycc[..., 1:] *= chroma
    ycc = hue_stage(ycc, H)
    if hue_delta is not None:
        ycc = hue_delta(ycc)
    rgb = ycc2rgb(ycc)
    return np.clip(rgb, 0, 1023) * 255.0 / 1023


def forward(cam, wb, M, p, **kw):
    """Camera RGB (black-subtracted, /white) -> sRGB 0..255."""
    y = (cam * wb) @ M.T
    return forward_lin(y, p, **kw)


# ---------- colour metrics ----------
def srgb2lab(rgb):
    c = np.clip(rgb, 0, 255) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    Mx = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ Mx.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def de76(a, b):
    return np.linalg.norm(srgb2lab(a) - srgb2lab(b), axis=-1)
