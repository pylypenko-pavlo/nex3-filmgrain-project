"""RAW loading for NEX-3N ARW: half-res camera RGB (black-subtracted, /white), EXIF meta."""
import json, subprocess, numpy as np, rawpy

def meta(path):
    """EXIF fields needed by the pipeline (exiftool)."""
    tags = ['CreativeStyle', 'Sony:Saturation', 'Sony:Contrast', 'Sony:Sharpness', 'WhiteBalance', 'ColorMatrix',
            'WB_RGGBLevels', 'WB_RGBLevels', 'BlackLevel', 'WhiteLevel', 'ISO', 'ExposureTime', 'FNumber']
    num = {'ColorMatrix', 'WB_RGGBLevels', 'WB_RGBLevels', 'BlackLevel', 'WhiteLevel', 'ISO', 'ExposureTime', 'FNumber'}
    out = subprocess.run(['exiftool', '-j'] + ['-' + t + ('#' if t in num else '') for t in tags] + [path],
                         capture_output=True, text=True).stdout
    m = json.loads(out)[0]
    for k in ('Saturation', 'Contrast', 'Sharpness'):
        if 'Sony:' + k in m:
            m[k] = m.pop('Sony:' + k)
    for k in ('Saturation', 'Contrast', 'Sharpness'):
        m[k] = int(str(m.get(k, 0)).replace('+', ''))
    for k in ('ColorMatrix', 'WB_RGGBLevels', 'WB_RGBLevels', 'BlackLevel', 'WhiteLevel'):
        if k in m and isinstance(m[k], str):
            m[k] = [float(x) for x in m[k].split()]
    return m

def load_cam(path):
    """Half-resolution camera RGB: each 2x2 Bayer quad -> (R, mean(G1,G2), B).
    Values: (raw - black) / (white - black), not white-balanced, linear."""
    with rawpy.imread(path) as r:
        raw = r.raw_image_visible.astype(np.float32)
        cols = r.raw_colors_visible
        black = np.array(r.black_level_per_channel, np.float32)
        white = float(r.white_level)
        desc = r.color_desc.decode()
    h, w = raw.shape; h -= h % 2; w -= w % 2
    raw = raw[:h, :w]; cols = cols[:h, :w]
    raw = raw - black[cols]
    out = np.zeros((h // 2, w // 2, 3), np.float32); cnt = np.zeros(3, np.float32)
    for dy in (0, 1):
        for dx in (0, 1):
            c = cols[dy, dx]; ch = desc[c]
            idx = 'RGB'.index(ch)
            out[..., idx] += raw[dy::2, dx::2]; cnt[idx] += 1
    out /= cnt
    out /= (white - black.mean())
    return out


def wb_gains(m):
    """Applied white-balance gains (R, G, B) from ARW SR2 WB_RGGBLevels (/1024 = G).
    Note: Sony WB_RGBLevels (also in JPEG) is the AWB estimate, NOT the applied gains (checked on DSC09431-38)."""
    v = np.array(m['WB_RGGBLevels'], float)
    return np.array([v[0], (v[1] + v[2]) / 2, v[3]]) / ((v[1] + v[2]) / 2)
