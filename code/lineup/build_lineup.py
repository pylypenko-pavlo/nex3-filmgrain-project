#!/usr/bin/env python3
"""Colour-slot lineup v7: Velvia 50 / House / Portra 400 / SantaColor 800 (proxy) / Phoenix / Acros.

OFFLINE ONLY. Nothing here talks to the camera. Reads the owner's local stock Backup blocks,
computes the designed values (matrices, hue-record moves, shared 3D-LUT deltas, slider values),
writes (a) data/looks/lineup_v7.json  = decoded designed values (no firmware bytes), and
       (b) write-ready hex blocks in ~/nex3n-dump/work/bk/lineup_v7/ (local, never committed).
Atlas page: atlas/colour-slots-lineup.md. Run with the numpy+scipy venv:
    ~/nex3n-dump/work/venv/bin/python -I code/lineup/build_lineup.py
"""
import json, os, struct, sys
import numpy as np
from scipy.optimize import least_squares

HOME = os.path.expanduser("~")
BK = HOME + "/nex3n-dump/work/bk/"
REPO = HOME + "/nex3n-research/"
OUT_LOCAL = BK + "lineup_v7/"

# ---------------------------------------------------------------- conventions (verified, see atlas)
M0 = np.array([[1292, -180, -88], [-44, 1340, -272], [-24, -108, 1156]], float) / 1024  # stock Standard (C-COL-005)
W709 = np.array([0.2126, 0.7152, 0.0722])
SLOT_BOOST = {0: 1.00, 1: 1.11, 2: 1.00, 3: 1.14, 4: 1.14}  # style's own chroma gain over Standard (E-0012; C-COL-012 disputed)
SAT_SLIDER_GAIN = 1.12                                          # measured +1 step: 43.7 -> 48.1 (C-COL-011 says 1.13)
CAP = 60                 # per-plane cap of the film delta (stock LUT itself reaches -55 at the corners; final byte clamp +-63)
LUT_UNIT_CODES = 0.237   # chroma codes (8-bit Cb/Cr) per LUT int8 unit; from E-0067: +63 -> da* +13.9 at Y'~134 (0.93 a*/code)


def S(k):  # uniform (de)saturation, keeps grey and luma (C-COL-010)
    return k * np.eye(3) + (1 - k) * np.outer(np.ones(3), W709)


def to_int(M, fix_rowsum=None):
    Mi = np.round(M).astype(int)
    if fix_rowsum is not None:
        for i in range(3):
            Mi[i, i] += fix_rowsum - Mi[i].sum()
    return Mi


# ---------------------------------------------------------------- colour helpers (sRGB D65)
Mx = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
Minv = np.linalg.inv(Mx)
WP = np.array([0.95047, 1.0, 1.08883])


def lab2lin(L, a, b):
    fy = (L + 16) / 116; fx = fy + a / 500; fz = fy - b / 200
    f = lambda t: np.where(t ** 3 > 216 / 24389, t ** 3, (116 * t - 16) / (24389 / 27))
    return np.stack([f(fx), f(fy), f(fz)], -1) * WP @ Minv.T


def lin2lab(l):
    xyz = l @ Mx.T / WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def Tparam(x):  # rows sum to 1 => neutral axis preserved
    T = np.zeros((3, 3))
    for i in range(3):
        j = [k for k in range(3) if k != i]
        T[i, j[0]] = x[2 * i]; T[i, j[1]] = x[2 * i + 1]; T[i, i] = 1 - x[2 * i] - x[2 * i + 1]
    return T


def fit_T_hue_targets(ratio, shift, g0, maxM=1700, ridge=0.02):
    """12-hue balanced fit (Lab h=0,30..330; L 35/55/75; C 20/35/50 - chroma ratio is ~C-independent, Fuji note 2c)."""
    src, tgt = [], []
    for h in range(0, 360, 30):
        for L in (35, 55, 75):
            for C in (20, 35, 50):
                lin = lab2lin(np.array([L]), np.array([C * np.cos(np.radians(h))]), np.array([C * np.sin(np.radians(h))]))[0]
                if lin.min() < 0.002 or lin.max() > 0.98:
                    continue
                r, s = ratio[h // 30], shift[h // 30]
                src.append(lin); tgt.append([L, C * r * np.cos(np.radians(h + s)), C * r * np.sin(np.radians(h + s))])
    src = np.array(src); tgt = np.array(tgt)

    def res(x):
        T = Tparam(x); d = lin2lab(np.clip(src @ T.T, 0, None)) - tgt
        M = T @ M0 * 1024
        return np.concatenate([d[:, 1], d[:, 2], 0.2 * d[:, 0], ridge * 10 * (T - S(g0)).ravel(), [max(np.abs(M).max() - maxM, 0) / 20]])
    Tk = S(g0); x0 = np.array([Tk[0, 1], Tk[0, 2], Tk[1, 0], Tk[1, 2], Tk[2, 0], Tk[2, 1]])
    T = Tparam(least_squares(res, x0).x)
    d = lin2lab(np.clip(src @ T.T, 0, None)) - tgt
    return T, float(np.sqrt(np.mean(d[:, 1] ** 2 + d[:, 2] ** 2)))


# ---------------------------------------------------------------- Velvia targets (measured, 30-degree Lab hue bins h=0..330)
#   comparator = friimaind corpus, Provia->Velvia, 3 scenes, 35<L<75, 20<C<55 (this work; None = no pixels)
#   abpy       = abpy/FujifilmCameraProfiles LUT, L55 C35 (notes/fuji-film-simulation-research.md 2c)
COMP_R = [1.16, 1.23, 1.20, 1.37, 1.20, 1.33, 1.19, None, 1.31, 1.36, 1.27, 1.20]
COMP_S = [-1.7, 4.1, 5.7, 2.8, 4.2, -1.7, -1.2, None, 15.5, 10.4, 2.4, -1.6]
ABPY_R = [1.16, 1.11, 1.25, 1.17, 1.15, 1.08, 1.02, 1.01, 1.11, 1.24, 1.40, 1.41]
ABPY_S = [-4, 4, 1, 2, 0, -3, -1, 13, 16, 10, 2, -1]
avg = lambda a, b: [np.mean([x for x in (p, q) if x is not None]) for p, q in zip(a, b)]
VEL_R, VEL_S = avg(COMP_R, ABPY_R), avg(COMP_S, ABPY_S)


def read_hex(path):
    return bytes(int(x, 16) for x in open(path).read().split())


def main():
    stock = read_hex(BK + "00030001_orig.txt")
    v5 = read_hex(BK + "00030001_looks_v5.hex")
    assert len(stock) == len(v5) == 1536

    # ---------------- slot 0: Velvia 50 (Standard slot, boost 1.00); saturation slider +1 carries x1.12
    T_vel, err_vel = fit_T_hue_targets([r / SAT_SLIDER_GAIN for r in VEL_R], VEL_S, 1.06)
    M0_vel = to_int(T_vel @ M0 * 1024, fix_rowsum=1024)
    # ---------------- slot 1: House (Vivid slot, boost 1.11): T from v3 (house-phoenix-looks.md), slot = S(1/b).T.M0
    v3 = json.load(open(REPO + "data/looks/v3_looks.json"))
    T_house = np.array(v3["house"]["T"]); T_phx = np.array(v3["phoenix"]["T"])
    M1_house = to_int(S(1 / SLOT_BOOST[1]) @ T_house @ M0 * 1024)
    # ---------------- slot 2: Portra 400 (Portrait slot, boost 1.00): Maraver chart fit (data/looks/looks_v1.json)
    M2_portra = np.array([[1146, 10, -132], [53, 1277, -306], [-21, -50, 1095]])
    # optional warm variant: M.diag(r,1,b), C-COL-032 (hypothesis)
    M2_portra_warm = to_int(M2_portra @ np.diag([1.03, 1.0, 0.97]))
    # ---------------- slot 3 / 4: unchanged from v5 (UltraMax proxy for Santa 800; Phoenix II)
    mat = lambda blk, s: np.array(struct.unpack_from("<9h", blk, 0x48 + 18 * s)).reshape(3, 3)
    M3_santa = mat(v5, 3); M4_phx = mat(v5, 4)
    assert (M4_phx == to_int(S(1 / SLOT_BOOST[4]) @ T_phx @ M0 * 1024)).all()
    # Santa alt (spektrafilm Portra 800 shape, 'direction labels' only): S(1/1.14) applied to the SF-CA2 matrix
    M3_santa_alt = to_int(S(1 / SLOT_BOOST[3]) @ np.array([[1340, -108, -208], [-60, 1272, -188], [-20, -21, 1065]], float))
    # ---------------- slot 5: B&W / Acros - stock matrix kept; optional channel-mix matrix (unverified slot)
    T_ac = np.array([[0.7427, 0.2864, -0.0291], [0.0172, 0.9643, 0.0185], [0.0496, 0.0155, 0.9349]])  # fit_T mono, rms 2.68 vs 3.12 code
    M5_acros_opt = to_int(T_ac @ M0 * 1024, fix_rowsum=1024)

    new = {0: M0_vel, 1: M1_house, 2: M2_portra, 3: M3_santa, 4: M4_phx}
    for s, M in new.items():
        d = np.linalg.det(M / 1024.0)
        assert d > 0 and np.abs(M).max() < 3000, (s, d)

    # ---------------- hue records (+0x100 + 24*r, int8): move the film delta with the film (v5 delta over stock)
    rec = lambda blk, r: np.array(struct.unpack_from("<24b", blk, 0x100 + 24 * r), int)
    d_portra = rec(v5, 1) - rec(stock, 1)      # Portra lived in slot 1 (v5)
    d_house = rec(v5, 2) - rec(stock, 2)       # House lived in slot 2 (v5)
    recs = {0: rec(v5, 0), 1: rec(stock, 1) + d_house, 2: rec(stock, 2) + d_portra, 3: rec(v5, 3), 4: rec(v5, 4)}
    for r in recs.values():
        assert r.min() >= -128 and r.max() <= 127

    # ---------------- 0x30001 / 0x30008 block v7 = v5 with the changes above
    blk = bytearray(v5)
    for s, M in new.items():
        struct.pack_into("<9h", blk, 0x48 + 18 * s, *[int(x) for x in M.ravel()])
    for r in (1, 2):                              # slots 0,3,4 records are byte-identical to v5
        struct.pack_into("<24b", blk, 0x100 + 24 * r, *[int(x) for x in recs[r]])
    changed = [i for i in range(1536) if blk[i] != v5[i]]

    # ---------------- shared 3D LUT (Backup 0x30004 and 0x30005 written identically)
    def lut_delta(m_by_y, tint_by_y=None, wfun=None):
        """int8 deltas [plane][Y][Cb][Cr]; plane0=dY (untouched), plane1=dCb, plane2=dCr. node c = (idx-4)*32 codes."""
        d = np.zeros((3, 5, 9, 9))
        for y in range(5):
            for cb in range(9):
                for cr in range(9):
                    cbv, crv = (cb - 4) * 32, (cr - 4) * 32
                    rad = np.hypot(cbv, crv)
                    d[1, y, cb, cr] = (m_by_y[y] - 1) * cbv / LUT_UNIT_CODES
                    d[2, y, cb, cr] = (m_by_y[y] - 1) * crv / LUT_UNIT_CODES
                    if tint_by_y is not None:
                        w = wfun(rad)
                        d[1, y, cb, cr] += w * tint_by_y[y][0] / LUT_UNIT_CODES
                        d[2, y, cb, cr] += w * tint_by_y[y][1] / LUT_UNIT_CODES
                    v = np.array([d[1, y, cb, cr], d[2, y, cb, cr]])
                    sc = min(1.0, CAP / max(np.abs(v).max(), 1e-9))   # vector cap: keeps the hue direction, max |shift| = CAP units
                    d[1, y, cb, cr], d[2, y, cb, cr] = v * sc
        return np.round(d).astype(int)

    def apply_lut(stock_hex_path, delta):
        base = np.frombuffer(read_hex(stock_hex_path)[:1215], dtype=np.int8).astype(int).reshape(3, 5, 9, 9)
        out = np.clip(base + delta, -63, 63)
        return out, int((np.abs(base + delta) > 63).sum())

    M_SHARED = [0.70, 0.90, 1.00, 0.95, 0.85]          # starting estimate (tune on camera)
    shared = lut_delta(M_SHARED)
    lut = {}
    for name in ("00030004", "00030005"):
        out, nclip = apply_lut(BK + name + "_orig.txt", shared)
        raw = bytearray(read_hex(BK + name + "_orig.txt"))
        raw[:1215] = out.astype(np.int8).tobytes()
        lut[name] = (bytes(raw), nclip)

    # conditional Phoenix II block for 0x30006 (ONLY if experiment S-1 shows Sunset reads it); stock 0x30006 is all-zero
    w_tint = lambda rad: 1.0 if rad <= 32 else (0.5 if rad <= 64 else 0.25)
    M_PHX = [0.35, 0.70, 1.00, 1.00, 1.00]             # scans: shadow chroma 2.2 vs 8.5 (house-phoenix-looks 2)
    TINT_PHX = [(0, 0), (0, 0), (0.0, 2.4), (0.7, 3.4), (0.0, 0.0)]   # (dCb, dCr) codes: scans neutral a*+1.2/+2.2, b* -1.4/-2.3 vs Standard (-1,-1.5)
    phx = lut_delta(M_PHX, TINT_PHX, w_tint)
    phx_blk = bytearray(1280); phx_blk[:1215] = np.clip(phx, -63, 63).astype(np.int8).tobytes()

    # ---------------- sliders (Backup 0x0107xxxx, 1 signed byte each, attr 0x60): contrast / saturation / sharpness per style
    sliders = {
        "slot0 Standard->Velvia50": {"contrast": ("0x01070735", +1), "saturation": ("0x01070742", +1), "sharpness": ("0x0107074f", +1)},
        "slot1 Vivid->House":       {"contrast": ("0x01070736", -3), "saturation": ("0x01070743", 0),  "sharpness": ("0x01070750", 0)},
        "slot2 Portrait->Portra400": {"contrast": ("0x0107073a", -1), "saturation": ("0x01070747", 0),  "sharpness": ("0x01070754", 0)},
        "slot3 Landscape->Santa800": {"contrast": ("0x0107073b", 0), "saturation": ("0x01070748", 0),  "sharpness": ("0x01070755", 0)},
        "slot4 Sunset->Phoenix":    {"contrast": ("0x0107073c", -3), "saturation": ("0x01070749", 0),  "sharpness": ("0x01070756", -1)},
        "slot5 B&W->Acros":         {"contrast": ("0x0107073d", +1), "saturation": None,               "sharpness": ("0x01070757", +1)},
    }

    # ---------------- outputs
    os.makedirs(OUT_LOCAL, exist_ok=True)
    hexs = lambda b: " ".join("%02x" % x for x in b)
    open(OUT_LOCAL + "00030001_lineup_v7.hex", "w").write(hexs(blk))
    open(OUT_LOCAL + "00030008_lineup_v7.hex", "w").write(hexs(blk))
    for name in lut:
        open(OUT_LOCAL + name + "_lineup_v7.hex", "w").write(hexs(lut[name][0]))
    open(OUT_LOCAL + "00030006_lineup_v7_phoenix_CONDITIONAL.hex", "w").write(hexs(phx_blk))

    dj = {
        "name": "lineup_v7",
        "note": "Decoded designed values only (no firmware bytes). Atlas: atlas/colour-slots-lineup.md. Slot matrices int16 1024=1.0 at 0x30001/0x30008 +0x48+18*slot; hue records int8 at +0x100+24*slot; shared LUT deltas int8 [plane][Ynode][Cb][Cr], byte offset plane*405+Y*81+Cb*9+Cr, ADDED to the stock LUT (clamped +-63).",
        "constants": {"slot_boost": SLOT_BOOST, "sat_slider_gain": SAT_SLIDER_GAIN, "lut_unit_codes": LUT_UNIT_CODES, "lut_delta_cap": CAP},
        "matrices": {str(s): M.tolist() for s, M in new.items()},
        "matrix_slot5_stock": mat(stock, 5).tolist(),
        "matrix_options": {"portra_warm_r1.03_b0.97": M2_portra_warm.tolist(), "santa_alt_portra800_shape": M3_santa_alt.tolist(), "acros_channel_mix_slot5_UNVERIFIED": M5_acros_opt.tolist()},
        "velvia_fit": {"T": T_vel.tolist(), "rms_dab": err_vel, "targets_ratio": VEL_R, "targets_hue_shift": VEL_S},
        "hue_records": {str(r): recs[r].tolist() for r in recs},
        "block_0x30001_changed_byte_offsets_vs_v5": changed,
        "lut_shared": {"m_by_Ynode": M_SHARED, "nonzero_delta_bytes_plane1": int((shared[1] != 0).sum()), "nonzero_delta_bytes_plane2": int((shared[2] != 0).sum()),
                        "clamped_nodes_0x30004": lut["00030004"][1], "clamped_nodes_0x30005": lut["00030005"][1],
                        "delta_plane1": shared[1].tolist(), "delta_plane2": shared[2].tolist()},
        "lut_phoenix_conditional_0x30006": {"m_by_Ynode": M_PHX, "tint_codes_(dCb,dCr)_by_Ynode": TINT_PHX, "delta_plane1": phx[1].tolist(), "delta_plane2": phx[2].tolist()},
        "sliders": sliders,
    }
    json.dump(dj, open(REPO + "data/looks/lineup_v7.json", "w"), indent=1)

    # ---------------- console summary (pasted into the atlas page)
    np.set_printoptions(linewidth=140)
    print("Velvia fit rms dab %.2f" % err_vel)
    for s, M in new.items():
        print("slot%d" % s, M.tolist(), "rowsums", M.sum(1).tolist(), "det %.2f" % np.linalg.det(M / 1024.0))
    print("Portra warm option", M2_portra_warm.tolist(), M2_portra_warm.sum(1).tolist())
    print("Santa alt", M3_santa_alt.tolist(), M3_santa_alt.sum(1).tolist())
    print("Acros opt", M5_acros_opt.tolist())
    print("hue records:", {r: recs[r].tolist() for r in recs})
    print("0x30001 changed bytes vs v5:", len(changed), "range", hex(min(changed)), hex(max(changed)))
    print("shared LUT nonzero deltas p1/p2:", dj["lut_shared"]["nonzero_delta_bytes_plane1"], dj["lut_shared"]["nonzero_delta_bytes_plane2"], "clamped", lut["00030004"][1], lut["00030005"][1])
    print("shared LUT Y-node ring examples (plane2 dCr, Cb=4 row, Cr idx 5..8):")
    for y in range(5):
        print("  Y%d" % y, shared[2, y, 4, 5:].tolist(), " plane1 col Cr=4, Cb idx 5..8:", shared[1, y, 5:, 4].tolist())
    print("Phoenix LUT neutral-ring tints (plane2 dCr at Cb4,Cr4):", [int(phx[2, y, 4, 4]) for y in range(5)], "(plane1 dCb):", [int(phx[1, y, 4, 4]) for y in range(5)])


if __name__ == "__main__":
    main()
