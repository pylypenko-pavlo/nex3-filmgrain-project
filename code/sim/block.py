"""Backup block 0x00030001 (1536 bytes): per-style matrices and hue tables.

Matrix of slot s: 9 x int16 LE at +0x48 + 18*s (1.0 = 1024), acts in linear light.
Hue record of slot s: 24 x int8 at +0x100 + 24*s = 6 quads x 4 hue regions
(region j: 0 red/skin/magenta, 1 orange/yellow/yellow-green, 2 cyan/sky, 3 blue/violet).
"""
import json
import os
import re

import numpy as np

BK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'looks', 'blocks') + os.sep
STYLE_SLOT = {'standard': 0, 'vivid': 1, 'portrait': 2, 'landscape': 3, 'sunset': 4}


def from_json(path):
    """Decoded block JSON (data/looks/blocks/*.json) -> 1536-byte buffer with the matrix and hue-table regions filled.
    Only those regions are used by the simulator; all other bytes are zero."""
    d = json.load(open(path))
    b = bytearray(1536)
    for s, m in enumerate(d['matrices']):
        b[0x48 + 18 * s:0x48 + 18 * s + 18] = np.asarray(m, '<i2').tobytes()
    for s, t in enumerate(d['hue_tables']):
        b[0x100 + 24 * s:0x100 + 24 * s + 24] = np.asarray(t, 'i1').tobytes()
    return bytes(b)


def load(path):
    """A hex dump of property 0x00030001 (any whitespace, user-supplied) or a decoded block JSON.
    Bare names ('looks_v5', '00030001_looks_v5.hex', 'orig') are looked up in data/looks/blocks/."""
    if not os.path.exists(path):
        name = re.sub(r'^00030001_|\.(hex|txt|json)$', '', os.path.basename(path))
        path = BK + name + '.json'
    if path.endswith('.json'):
        return from_json(path)
    b = bytes.fromhex(re.sub(r'[^0-9a-fA-F]', '', open(path).read()))
    if len(b) != 1536:
        raise ValueError(f'{path}: {len(b)} bytes, expected 1536')
    return b


def matrix(b, slot):
    return np.frombuffer(b, '<i2', 9, 0x48 + 18 * slot).reshape(3, 3).astype(float)


def table(b, slot):
    return np.frombuffer(b, 'i1', 24, 0x100 + 24 * slot).reshape(6, 4).astype(float)


def orig():
    return load('orig')


# Which block was in the camera for a frame number (from the session log).
# None = unknown. Only needed for JPEG-mode re-rendering (EXIF does not record the tables).
_SESSIONS = [
    (9200, 9395, 'orig'), (9416, 9430, 'orig'), (9431, 9433, 'test1'), (9434, 9439, 'tags'),
    (9440, 9455, 'looks_v1'), (9468, 9472, 'v3_e1'), (9473, 9477, 'binary'), (9478, 9482, 'bytes'),
    (9483, 9487, 'looks_v3'), (9488, 9492, 'bands'), (9493, 9497, 'looks_v4'), (9498, 9510, 'looks_v5'),
]


def known_block(n):
    for a, b, k in _SESSIONS:
        if a <= n <= b:
            return orig() if k == 'orig' else load('00030001_%s.hex' % k), k
    return None, None
