#!/usr/bin/env python3
"""Batch preview: render real frames with every look slot of a block and build a contact sheet.

batch.py --block looks_v5 [--src a.JPG b.ARW ...] [--styles standard,vivid,portrait,landscape,sunset]
         [--curve film] [--width 640] --out sheet.jpg
Sources: ARW (RAW mode, as-shot WB) or camera JPEG (JPEG mode; source block from the session log or --src-block).
Default sources: Standard frames of the 05.10 live sessions.
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageDraw

import block
import pipeline as pl
import rawio
import sim

DEFAULT = []  # pass your own frames with --src


def render(path, pp, blk, style, curve, src_block, width):
    path = os.path.expanduser(path)
    if path.upper().endswith('.ARW'):
        meta = rawio.meta(path); cam = rawio.load_cam(path)
        k = max(1, cam.shape[1] // width)
        cam = cam[:cam.shape[0] // k * k, :cam.shape[1] // k * k].reshape(cam.shape[0] // k, k, cam.shape[1] // k, k, 3).mean((1, 3))
        return pl.render_raw(cam, rawio.wb_gains(meta), blk, style, pp, 0, 0, curve), None
    meta = rawio.meta(path)
    im = Image.open(path).convert('RGB'); im = im.resize((width, int(im.height * width / im.width)), Image.BOX)
    n = int(os.path.basename(path)[3:8])
    sblk = sim.get_block(src_block) if src_block else block.known_block(n)[0]
    src = dict(block=sblk, style=meta['CreativeStyle'].lower(), contrast=meta['Contrast'], sat=meta['Saturation'])
    dst = dict(block=blk, style=style, contrast=0, sat=0, curve=curve)
    return pl.rerender_jpeg(np.asarray(im).astype(float), pp, src, dst), np.asarray(im)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--block', default='looks_v5')
    ap.add_argument('--src', nargs='*', default=DEFAULT)
    ap.add_argument('--src-block', default=None)
    ap.add_argument('--styles', default='standard,vivid,portrait,landscape,sunset')
    ap.add_argument('--curve', default=None)
    ap.add_argument('--k0', default='film', choices=['film', 'orig'])
    ap.add_argument('--width', type=int, default=640)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    sim.set_k0(a.k0)
    pp = pl.load_params(); blk = sim.get_block(a.block); styles = a.styles.split(',')
    rows = []
    for p in a.src:
        tiles = []; orig = None
        for st in styles:
            img, o = render(p, pp, blk, st, sim.get_curve(a.curve), a.src_block, a.width)
            orig = o if o is not None else orig
            tiles.append((st, img))
        if orig is not None:
            tiles.insert(0, ('camera JPEG', orig.astype(np.uint8)))
        h = min(t[1].shape[0] for t in tiles)
        row = Image.new('RGB', (sum(t[1].shape[1] for t in tiles), h + 24), 'white'); x = 0
        d = ImageDraw.Draw(row)
        for name, t in tiles:
            row.paste(Image.fromarray(t[:h]), (x, 24)); d.text((x + 6, 5), '%s | %s' % (os.path.basename(p), name), fill='black'); x += t.shape[1]
        rows.append(row)
    W = max(r.width for r in rows); sheet = Image.new('RGB', (W, sum(r.height for r in rows)), 'white'); y = 0
    for r in rows:
        sheet.paste(r, (0, y)); y += r.height
    sheet.save(a.out, quality=90)
    print('wrote', a.out, sheet.size)


if __name__ == '__main__':
    main()
