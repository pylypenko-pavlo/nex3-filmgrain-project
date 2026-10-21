"""NEX-3N JPEG pipeline simulator: production forward/inverse with fitted parameters (cache/params.npz).

Forward (RAW):   cam --WB--> x --M_slot--> y (linear) --F--> codes --tone(style o contrast)--> codes
                 --YCbCr: chroma*boost(style)*(1+k*sat) --> H0(hue) --> hue-table stage(record - Standard record)--> sRGB
Inverse (JPEG):  the same chain backwards (clipped values stay clipped) -> x (white-balanced camera RGB).

Chosen hypotheses (see notes/simulator.md): Sunset Q1 = -128 treated as 'use Standard values';
colour stages after the tone curve; Portrait style curve k1; no extra 3x3 before/after the slot matrix.
"""
import os

import numpy as np

import block
import hue
import model

HERE = os.path.dirname(os.path.abspath(__file__))
STYLES = ('standard', 'vivid', 'portrait', 'landscape', 'sunset')
BOOST_I = {'vivid': 0, 'portrait': 1, 'landscape': 2, 'sunset': 3}
PORTRAIT_CURVE = 1
T_STD = block.table(block.orig(), 0)


def load_params(path=os.path.join(HERE, 'cache', 'params.npz')):
    z = np.load(path, allow_pickle=True)
    x = z['x']; idx = {k: slice(a, b) for k, a, b in z['idx']}
    h0 = x[idx['H0']]
    return dict(F=x[idx['F']], gain=1.0, hue=hue.unpack(x[idx['hue']]), boost=x[idx['boost']],
                satk=float(x[idx['satk']][0]), H0=dict(gain=h0[:9], rot=h0[9:]))


def style_curve(style, contrast=0, curve=None):
    """1024-entry code->code curve = style curve o contrast curve.
    curve: None (camera default), 'kN' (av-cam curve N used as the STYLE curve), path to .npy (1024 values),
    or an array. The contrast slider curve k(3+c) is applied first."""
    T = model.TONE
    con = T[3 + int(contrast)]
    s = style.lower()
    if curve is None:
        st = T[14] if s in ('vivid', 'landscape', 'sunset') else T[PORTRAIT_CURVE] if s == 'portrait' else T[3]
    elif isinstance(curve, str) and curve.startswith('k'):
        st = T[int(curve[1:])]
    elif isinstance(curve, str) and curve.endswith('.json'):
        st = np.asarray(__import__('json').load(open(curve))['curve'], float)
    elif isinstance(curve, str):
        st = np.load(curve).astype(float)
    else:
        st = np.asarray(curve, float)
    if len(st) != 1024:
        raise ValueError('tone curve must have 1024 entries')
    return np.interp(con, np.arange(1024), st)


def delta_table(T):
    """Record minus the native Standard record; a whole quad of -128 (Sunset Q1 marker) = 'use Standard values'."""
    T = np.array(T, float).copy()
    for q in range(6):
        if np.all(T[q] == -128):
            T[q] = T_STD[q]
    return T - T_STD


def chroma_factor(pp, style, sat):
    s = style.lower()
    b = np.exp(pp['boost'][BOOST_I[s]]) if s in BOOST_I else 1.0
    return b * (1 + pp['satk'] * sat)


def _h0_inverse(ycc, H, it=8):
    out = ycc.copy()
    for _ in range(it):
        out[..., 1:] += ycc[..., 1:] - model.hue_stage(out, H)[..., 1:]
    return out


def forward_lin(y, pp, style, T, contrast=0, sat=0, curve=None):
    """post-matrix linear RGB (H,W,3) -> sRGB float 0..255"""
    e = model.base_gamma(np.maximum(y, 0), pp['F'])
    e = np.interp(np.clip(e, 0, 1023), np.arange(1024), style_curve(style, contrast, curve))
    ycc = model.rgb2ycc(e)
    ycc[..., 1:] *= chroma_factor(pp, style, sat)
    ycc = model.hue_stage(ycc, pp['H0'])
    ycc[..., 1:] = hue.apply(ycc[..., 1:], delta_table(T), pp['hue'])
    return np.clip(model.ycc2rgb(ycc), 0, 1023) * 255 / 1023


def inverse_lin(rgb, pp, style, T, contrast=0, sat=0, curve=None):
    """sRGB 0..255 (camera JPEG) -> post-matrix linear RGB (approximate where clipped)."""
    ycc = model.rgb2ycc(np.asarray(rgb, float) * 1023 / 255)
    ycc[..., 1:] = hue.apply(ycc[..., 1:], delta_table(T), pp['hue'], inverse=True)
    ycc = _h0_inverse(ycc, pp['H0'])
    ycc[..., 1:] /= chroma_factor(pp, style, sat)
    e = model.ycc2rgb(ycc)
    c = style_curve(style, contrast, curve)
    c = np.maximum.accumulate(c + np.arange(1024) * 1e-6)
    e = np.interp(np.clip(e, 0, 1023), c, np.arange(1024))
    # invert base gamma numerically
    ys = 2.0 ** np.linspace(-16, 2.5, 4000)
    fs = np.maximum.accumulate(model.base_gamma(ys, pp['F']) + np.arange(4000) * 1e-9)
    return np.interp(e, fs, ys)


def render_raw(cam, wb, blk, style, pp, contrast=0, sat=0, curve=None, matrix=None, ev=0.0):
    """cam: rawio.load_cam output; wb: 3 gains; blk: 1536-byte block; returns uint8 sRGB image."""
    slot = block.STYLE_SLOT[style.lower()]
    M = (np.asarray(matrix, float).reshape(3, 3) if matrix is not None else block.matrix(blk, slot)) / 1024.0
    y = (cam * wb * 2.0 ** ev) @ M.T
    return np.round(forward_lin(y, pp, style, block.table(blk, slot), contrast, sat, curve)).astype(np.uint8)


def rerender_jpeg(rgb, pp, src, dst):
    """JPEG-domain re-render. src/dst: dict(block=bytes, style=str, contrast=int, sat=int, curve=..., matrix=None);
    dst may also carry ev (stops) and wb (R,G,B gains relative to the source).
    Inverts the src chain to white-balanced camera RGB and renders it with dst."""
    def mat(d):
        return (np.asarray(d['matrix'], float).reshape(3, 3) if d.get('matrix') is not None
                else block.matrix(d['block'], block.STYLE_SLOT[d['style'].lower()])) / 1024.0
    ss = block.STYLE_SLOT[src['style'].lower()]; ds = block.STYLE_SLOT[dst['style'].lower()]
    y = inverse_lin(rgb, pp, src['style'], block.table(src['block'], ss), src.get('contrast', 0), src.get('sat', 0), src.get('curve'))
    x = y @ np.linalg.inv(mat(src)).T * 2.0 ** dst.get('ev', 0.0)
    if 'wb' in dst:  # optional WB change, gains relative to the source
        x = x * np.asarray(dst['wb'], float)
    y2 = x @ mat(dst).T
    out = forward_lin(y2, pp, dst['style'], block.table(dst['block'], ds), dst.get('contrast', 0), dst.get('sat', 0), dst.get('curve'))
    return np.round(out).astype(np.uint8)
