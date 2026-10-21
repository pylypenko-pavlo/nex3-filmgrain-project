#!/usr/bin/env python3
"""Render all 13 NEX-3N Creative Styles (6 confirmed + 7 hidden candidates) on clean frames.

Confirmed styles use real firmware params (matrix slot, style tone curve, chroma boost).
Hidden styles (Neutral/Clear/Deep/Light/Night/Autumn/Sepia) are rendered as CANDIDATE
approximations from Sony's documented character of each style on later bodies (a6000/A7),
because the 3N firmware does not expose a confirmable colormode->matrix/curve slot map
(see reference/nex3n-hidden-styles-render.md). All 7 are GUESSES, labelled "(guess)".
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

import block
import hue
import model
import pipeline as pl
import rawio
import sim

sim.set_k0('orig')  # depict stock firmware (owner's film k0 only affects Contrast -3)
PP = pl.load_params()
TONE = model.TONE
T_STD = block.table(block.orig(), 0)


def fwd(x, M, curve, chroma, T, sepia=False):
    """x: WB camera-RGB linear (H,W,3). M: 3x3 (1.0=1024). curve: 1024 array. -> uint8 sRGB."""
    y = x @ (np.asarray(M, float).reshape(3, 3) / 1024.0).T
    e = model.base_gamma(np.maximum(y, 0), PP['F'])
    e = np.interp(np.clip(e, 0, 1023), np.arange(1024), curve)
    ycc = model.rgb2ycc(e)
    ycc[..., 1:] *= chroma
    ycc = model.hue_stage(ycc, PP['H0'])
    if chroma > 0:
        ycc[..., 1:] = hue.apply(ycc[..., 1:], pl.delta_table(T), PP['hue'])
    rgb = model.ycc2rgb(ycc)
    if sepia:
        Y = np.clip(rgb @ np.array([0.299, 0.587, 0.114]), 0, 1023)
        rgb = np.stack([Y * 1.03, Y * 0.87, Y * 0.66], -1)  # warm sepia tint
    return np.clip(np.clip(rgb, 0, 1023) * 255 / 1023, 0, 255).astype(np.uint8)


def boost(name):
    return float(np.exp(PP['boost'][pl.BOOST_I[name]])) if name in pl.BOOST_I else 1.0


def curve(style_k, contrast=0):
    """style tone curve k after the contrast-slider curve k(3+contrast)."""
    con = TONE[3 + contrast]
    return np.interp(con, np.arange(1024), TONE[style_k])


def autumn_table():
    T = T_STD.copy()
    T[1, 0] += 45   # Q1 red saturation up
    T[1, 1] += 45   # Q1 yellow saturation up
    T[0, 0] -= 20   # Q0 red hue: warm (toward orange)
    return T

# (label, matrix slot, hue-table slot, forward curve, chroma, special, confirmed?)
def styles(b):
    M = lambda s: block.matrix(b, s)
    T = lambda s: block.table(b, s)
    return [
        ('Standard',        M(0), curve(3),            1.0,            T(0), False, True),
        ('Vivid',           M(1), curve(14),           boost('vivid'), T(1), False, True),
        ('Portrait',        M(2), curve(1, 1),         boost('portrait') * (1 + PP['satk'] * -1), T(2), False, True),
        ('Landscape',       M(3), curve(14),           boost('landscape'), T(3), False, True),
        ('Sunset',          M(4), curve(14),           boost('sunset'), T(4), False, True),
        ('B&W',             M(5), curve(3),            0.0,            T(0), False, True),
        ('Neutral (guess)', M(0), curve(1),            0.72,           T_STD, False, False),
        ('Clear (guess)',   M(0), curve(14),           1.06,           T_STD, False, False),
        ('Deep (guess)',    M(0), curve(15),           1.30,           T_STD, False, False),
        ('Light (guess)',   M(0), curve(17),           0.85,           T_STD, False, False),
        ('Night (guess)',   M(0), curve(0),            0.95,           T_STD, False, False),
        ('Autumn (guess)',  M(0), curve(14),           1.12,           autumn_table(), False, False),
        ('Sepia (guess)',   M(0), curve(3),            0.0,            T_STD, True, False),
    ]


def source_x(path, width):
    """Return WB camera-RGB linear (H,W,3) for a Standard source frame (RAW or JPEG)."""
    path = os.path.expanduser(path)
    if path.upper().endswith('.ARW'):
        meta = rawio.meta(path); cam = rawio.load_cam(path)
        k = max(1, cam.shape[1] // width)
        H, W = cam.shape[0] // k * k, cam.shape[1] // k * k
        cam = cam[:H, :W].reshape(H // k, k, W // k, k, 3).mean((1, 3))
        return cam * rawio.wb_gains(meta)
    im = Image.open(path).convert('RGB')
    im = im.resize((width, int(im.height * width / im.width)), Image.BOX)
    rgb = np.asarray(im).astype(float)
    b0 = block.orig()
    y = pl.inverse_lin(rgb, PP, 'standard', block.table(b0, 0), 0, 0, None)
    M0 = block.matrix(b0, 0) / 1024.0
    return y @ np.linalg.inv(M0).T


def main():
    width = 560
    srcs = sys.argv[1:] or [os.environ.get('NEX3N_FRAMES_DIR','.')+'/DSC09419.ARW',
                            os.environ.get('NEX3N_FRAMES_DIR','.')+'/DSC09414.JPG', os.environ.get('NEX3N_FRAMES_DIR','.')+'/DSC09408.JPG']
    b = block.orig()
    for p in srcs:
        x = source_x(p, width)
        tiles = []
        for lab, M, cv, ch, Ts, sep, conf in styles(b):
            tiles.append((lab, fwd(x, M, cv, ch, Ts, sep)))
        # 13 tiles -> grid 4 cols
        cols = 4
        tw, th = tiles[0][1].shape[1], tiles[0][1].shape[0]
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * tw, rows * (th + 18)), 'white')
        d = ImageDraw.Draw(sheet)
        for i, (lab, img) in enumerate(tiles):
            r, c = divmod(i, cols)
            y0 = r * (th + 18)
            sheet.paste(Image.fromarray(img), (c * tw, y0 + 18))
            d.text((c * tw + 4, y0 + 4), lab, fill='black')
        name = os.path.splitext(os.path.basename(p))[0]
        out = os.environ.get('OUT_DIR','out')+'/hidden_styles_%s.jpg' % name
        sheet.save(out, quality=90)
        print('wrote', out, sheet.size)


if __name__ == '__main__':
    main()
