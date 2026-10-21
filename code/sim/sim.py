#!/usr/bin/env python3
"""NEX-3N look simulator (offline, no camera access).

RAW mode:   sim.py --raw X.ARW --block looks_v5 --style vivid [--curve k14|film|file.npy] [--contrast 0] [--saturation 0]
                   [--matrix "1061,99,-136,..."] [--wb asshot|daylight|cloudy|shade|tungsten|...|R,B] [--full] --out preview.jpg
JPEG mode:  sim.py --jpg DSC09505.JPG [--src-block looks_v5] --block my.hex --style sunset --out preview.jpg
            (inverts the camera chain of the source frame; source style/sliders from EXIF, source block from the
             session log in block.py unless --src-block is given; clipped highlights stay clipped)
--block: hex dump path or a name in data/looks/blocks (orig, looks_v5, ...).
--curve replaces the STYLE curve (Vivid/Landscape/Sunset: k14, Portrait: k1, Standard: identity);
        the Contrast slider curve is applied first, as in the camera.
--k0 film|orig: what sits in av-cam curve k0 (= Contrast -3). The camera now has the film curve there (05.10).
"""
import argparse
import os

import numpy as np
from PIL import Image

import block
import model
import pipeline as pl
import rawio

FILM_K0 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'curves', 'film_k0.json')
_ORIG_K0 = model.TONE[0].copy()


def get_block(name):
    if name in (None, 'orig'):
        return block.orig()
    if os.path.exists(name):
        return block.load(name)
    if os.path.exists(block.BK + name + '.json'):
        return block.load(name)
    raise SystemExit('block not found: %s' % name)


def get_curve(c):
    if c is None:
        return None
    if c == 'film':
        return FILM_K0
    return c


def set_k0(which):
    model.TONE[0] = np.asarray(__import__('json').load(open(FILM_K0))['curve'], float) if which == 'film' else _ORIG_K0


def wb_from(meta, path, spec):
    if spec in (None, 'asshot'):
        return rawio.wb_gains(meta)
    if ',' in spec:
        r, b = map(float, spec.split(','))
        return np.array([r, 1.0, b])
    tag = 'WB_RGBLevels' + spec.capitalize()
    import json
    import subprocess
    v = json.loads(subprocess.run(['exiftool', '-j', '-%s#' % tag, path], capture_output=True, text=True).stdout)[0].get(tag)
    if v is None:
        raise SystemExit('no %s in EXIF' % tag)
    v = np.array([float(x) for x in str(v).split()])
    return v / v[1]


def load_cam_full(path):
    """Full-resolution demosaic (rawpy AHD, camera RGB, linear), scaled per channel to match rawio.load_cam."""
    import rawpy
    with rawpy.imread(path) as r:
        rgb = r.postprocess(output_bps=16, gamma=(1, 1), no_auto_bright=True, output_color=rawpy.ColorSpace.raw,
                            use_camera_wb=False, user_wb=[1, 1, 1, 1], user_flip=0).astype(np.float32) / 65535.0
    half = rawio.load_cam(path)
    k = half.reshape(-1, 3).mean(0) / rgb.reshape(-1, 3).mean(0)
    return rgb * k


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--raw'); g.add_argument('--jpg')
    ap.add_argument('--block', default='orig')
    ap.add_argument('--style', default=None, help='standard|vivid|portrait|landscape|sunset (default: from EXIF)')
    ap.add_argument('--contrast', type=int, default=None)
    ap.add_argument('--saturation', type=int, default=None)
    ap.add_argument('--curve', default=None)
    ap.add_argument('--matrix', default=None, help='9 ints (1.0 = 1024), overrides the block slot matrix')
    ap.add_argument('--wb', default='asshot')
    ap.add_argument('--ev', type=float, default=0.0, help='exposure shift in stops')
    ap.add_argument('--k0', default='film', choices=['film', 'orig'])
    ap.add_argument('--src-block', default=None)
    ap.add_argument('--full', action='store_true', help='RAW: full-resolution demosaic (slow); default half-res')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    set_k0(a.k0)
    pp = pl.load_params()
    blk = get_block(a.block)
    mat = [float(v) for v in a.matrix.split(',')] if a.matrix else None
    if a.raw:
        meta = rawio.meta(a.raw)
        jm = a.raw[:-4] + '.JPG'
        jmeta = rawio.meta(jm) if os.path.exists(jm) else meta
        style = (a.style or jmeta['CreativeStyle']).lower()
        con = jmeta['Contrast'] if a.contrast is None else a.contrast
        sat = jmeta['Saturation'] if a.saturation is None else a.saturation
        cam = load_cam_full(a.raw) if a.full else rawio.load_cam(a.raw)
        out = pl.render_raw(cam, wb_from(meta, a.raw, a.wb), blk, style, pp, con, sat, get_curve(a.curve), mat, a.ev)
    else:
        meta = rawio.meta(a.jpg)
        n = int(os.path.basename(a.jpg)[3:8]) if os.path.basename(a.jpg).startswith('DSC') else -1
        sblk, sname = (get_block(a.src_block), a.src_block) if a.src_block else block.known_block(n)
        if sblk is None:
            raise SystemExit('source block unknown for %s: pass --src-block' % a.jpg)
        src = dict(block=sblk, style=meta['CreativeStyle'].lower(), contrast=meta['Contrast'], sat=meta['Saturation'])
        dst = dict(block=blk, style=(a.style or src['style']).lower(),
                   contrast=src['contrast'] if a.contrast is None else a.contrast,
                   sat=src['sat'] if a.saturation is None else a.saturation, curve=get_curve(a.curve), matrix=mat, ev=a.ev)
        if a.wb not in (None, 'asshot'):
            if ',' not in a.wb:
                raise SystemExit('JPEG mode: --wb takes relative gains R,B (no EXIF presets)')
            r, b = map(float, a.wb.split(','))
            dst['wb'] = [r, 1.0, b]
        rgb = np.asarray(Image.open(a.jpg).convert('RGB')).astype(float)
        out = pl.rerender_jpeg(rgb, pp, src, dst)
        print('source: %s, style %s, block %s' % (os.path.basename(a.jpg), src['style'], sname))
    Image.fromarray(out).save(a.out, quality=92)
    print('wrote', a.out, out.shape)


if __name__ == '__main__':
    main()
