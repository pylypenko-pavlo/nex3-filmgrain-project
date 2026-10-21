# Colour-slot lineup v7: Velvia 50 / House / Portra 400 / SantaColor 800 / Phoenix / Acros (2026-10-12)

Offline design, camera not touched. Target (owner's lineup): slot 0 Standard = **Velvia 50**, 1 Vivid = **House 100**, 2 Portrait = **Portra 400**, 3 Landscape = **SantaColor 800**, 4 Sunset = **Phoenix 200 / Phoenix II**, 5 B&W = **Acros**.
Builds on `film-sim-targets.md` (lever mapping), `../notes/house-phoenix-looks.md` (matrix convention, House v3, Phoenix v3) and E-0067 (3D LUT proven). Scope: NEX-3N fw 1.00 only.

Files produced (all offline, reproducible):
- `code/lineup/build_lineup.py` - the builder (numpy+scipy venv `~/nex3n-dump/work/venv`).
- `data/looks/lineup_v7.json` - decoded designed values (matrices, hue records, LUT deltas, slider bytes). No firmware bytes.
- `~/nex3n-dump/work/bk/lineup_v7/*.hex` - write-ready blocks, local only (`*.hex` is git-ignored): `00030001_lineup_v7.hex` = `00030008_lineup_v7.hex` (md5 `e7dfca3d27cd99dc3c3414f959af6c13`), `00030004_lineup_v7.hex` (`7eef6dec319a236d214fbd3d80e65d7b`), `00030005_lineup_v7.hex` (`13e493ae5fa2c0abf341c8f39d029651`), `00030006_lineup_v7_phoenix_CONDITIONAL.hex` (`6b6282e0a2d6d7e39a2f6b5700410def`, do NOT write before experiment S-1).

Evidence tags: **[measured]** numbers computed from comparator frames / charts / scans; **[verified-hw]**, **[verified-code]** as in the atlas; **[estimate]** = *starting estimate (tune on camera)*; **[hypothesis]**.
Colour-source IP note: the parvec preset numbers are the creator's work and stay local (as in `film-sim-targets.md`); this page only carries values we derived from them (direction, rough size, fit residuals).

---

## 0. Read first: what the levers can and cannot do per slot

| lever | scope | where | consequence for the lineup |
|---|---|---|---|
| colour matrix 3x3 | **per slot** | Backup `0x30001`+`0x30008` `+0x48+18*slot` (int16 LE, 1024 = 1.0) | main per-film hue/chroma; row sums != 1024 tint greys (warmth) |
| hue record (6 quads x 4 int8) | **per slot** | same blocks `+0x100+24*slot` | small per-film hue trims; **moves with the film** (section 2) |
| contrast / saturation / sharpness sliders | **per slot** | Backup `0x0107xxxx`, 1 signed byte each | contrast selects tone curve k0..k6; saturation x(1+~0.12 s) |
| tone curves k0..k6 | **global constants** | p3 av-cam `0x5b006a + 0x800*k` (not Backup) | per slot only *which* of 7 fixed shapes; k0 = film curve already flashed (`current_p3`) |
| chroma-by-luminance 3D LUT | **shared, not per slot** (see below) | Backup `0x30004` + `0x30005` | one film-common baseline for slots 0,1,2,3,5; no per-film split-tone |
| Sunset LUT | Sunset only | block unknown (`0x30006`? `0x30007`? off?) | Phoenix has no LUT control until experiment S-1 |

**Key finding of this pass (changes the plan): the 3D LUT is one LUT for all styles except Sunset.**
- [verified-hw] E-0067 wrote the same edit to `0x30004` and `0x30005`; 5 of 6 styles responded with similar size (Standard +13.9, Vivid +12.7, Portrait +10.1, Landscape +11.8, B&W +18.5 a*).
- [verified-code, partly traced 2026-10-12] the dispatcher `0x3d12f8` (VA `0xc38122f8`) reads **one** selector byte `[p8+0x4a]` (`p8 = obj[8]`): bits 0-3 = block index, bits 5-6 = kind, bit 4 = flag, `0xff` = LUT off. Kind 0 = 3D LUT: index 0 / 1 / 2 -> RAM copies `0xc3ac3494` / `0xc3ac3994` / `0xc3ac3e94` = Backup **`0x30004` / `0x30005` / `0x30006`** (literal pools at `0x3d15c4`, `0x3d15c8`, `0x3d15c0`, checked against the master pointer table at `0x61d784`). Kind 1 = 2-D LUT: base `0xc3ac4394` = Backup **`0x30007`**, variant `i` at `+0xa2*i` (3 variants of 2 x 9 x 9 bytes, no Y axis). That byte is **not derived from the Creative Style**: the builder at `0x2ea930` (VA `0xc372b930`, store at `0x2eac72`) fills it from a mode-indexed RAM table at `*obj0 + 0x2e0` (`obj0 = obj[0]`; helper `0x2eb038`, bytes `+8,+0xa,+0xc,+0xe,+0x10,+0x14`, picked by `p8[2]`, probably the LutMode CAP/MOV/MON, and two `obj0` flags) and a 44-way switch on `obj0[0x1b]` (dispatch at `0x2ea9ee`, byte table at `0x2ea9f8`). The style index `obj0[0x26]` only yields a *class* (Vivid -> 1, style 12 "Real" -> 2, else 0) stored in the **neighbouring** byte `p8+0x49`, which a different dispatcher consumes (not traced; candidate consumer of the per-slot hue records, C-COL-027).
- Residual uncertainty: which of the two blocks (`0x30004` vs `0x30005`) the stills path uses, and whether two style classes pick different blocks (`tbl[+0x10]` vs `tbl[+0x14]`, chosen by `obj0[0x20+0x1a]`). E-0067 cannot tell (both edited). Writing both blocks identically (as E-0067) is safe under every case. Experiment M-1 (section 9) settles it.
- Likely corollary [hypothesis]: for some values of `obj0[0x1b]` the switch stores `0xff` (LUT off); which modes those are is not decoded (perhaps the automatic and scene modes). Verify in P/A/S/M only (E-0067 was shot in a manual mode).

So: **per-film split-toning (cool shadows / warm highlights per stock) cannot be realised per slot.** What each slot gets: its own matrix (+ highlight-weighted warmth through row sums), hue record, tone curve choice, saturation, sharpness; the LUT carries what all six films share (clean shadows, soft highlight chroma, neutral axis untouched). The per-film *ideal* LUT parameters are kept in section 5 for Sunset (if reachable) and for any future per-style selector.

Other standing facts used below:
- Tone is selected per slot by the **contrast slider**: -3..+3 = k0..k6, k3 identity [verified-hw, C-TONE-002]; any non-zero slider switches the style's own curve off (Vivid/Landscape/Sunset k14, C-TONE-010).
- B&W (slot 5): slot index is **unverified** (C-COL-004); there is **no saturation slider** (BKID triple `073d/-/0757`, C-CTRL-013); chroma is zero *before* the LUT (B&W pre-edit a* = 0.000, E-0067), so any neutral-axis tint in the shared LUT would tone the B&W (B&W was the most sensitive style: +18.5 a* from one node).
- The matrices of v5 (on the camera now: Vivid = Portra 400, Portrait = House, Landscape = UltraMax 400, Sunset = Phoenix II) were designed *for their old slots*; every film carries its slot's chroma boost (Vivid x1.11, Landscape/Sunset x1.14, Portrait x1.00, E-0012), so House and Portra **swap slots with a re-fit**, not a copy.
- Camera state precondition (START-HERE): the camera is on **EXP-11** (reboots on high-ISO capture). Backup writes do not need p3, but verification shots do: flash `current_p3.bin` (md5 `d7cca446...`) first.

---

## 1. The lineup (slot -> film -> levers -> addresses -> values -> source)

All colour-block writes go to **both** `0x00030001` and `0x00030008` (identical). Offsets are inside the block; matrices int16 LE, row-major `[R-row; G-row; B-row]`, 1024 = 1.0.

| slot | style label now | film | matrix @ `+off` (int16) | row sums | hue record @ `+off` | contrast -> k | sat | sharp | source / flag |
|---|---|---|---|---|---|---|---|---|---|
| 0 | Standard | **Velvia 50** | `1243,-121,-98 / -63,1504,-417 / -69,-113,1206` @`+0x48` | 1024 x3 | stock (`+0x100` unchanged) | **+1 -> k4** | **+1** | +1 | fit to Fuji Velvia, Provia->Velvia, mean of two measured tables [measured]; boost split matrix x slider [estimate] |
| 1 | Vivid | **House 100** | `1030,84,-75 / 32,1182,-191 / 10,76,912` @`+0x5a` | 1039 / 1023 / 998 | `+0x118`: House delta moved from v5 slot 2 | **-3 -> k0** | 0 | 0 | House v3 `T` x Vivid boost 1/1.11 [measured: refs + chart]; k0 = film curve designed from the same refs |
| 2 | Portrait | **Portra 400** | `1146,10,-132 / 53,1277,-306 / -21,-50,1095` @`+0x6c` | 1024 x3 | `+0x130`: Portra delta moved from v5 slot 1 | **-1 -> k2** | 0 | 0 | Maraver chart fit, Portrait boost 1.00 [measured, E-0012 for the boost]; tone [estimate] |
| 3 | Landscape | **SantaColor 800** (proxy: UltraMax 400) | unchanged from v5: `1391,-79,-288 / 28,1270,-274 / 31,-40,1033` @`+0x7e` | 1024 x3 | unchanged (`+0x148`) | 0 (native k14) | 0 | 0 | **no SantaColor 800 data exists** (film-colorchecker-tests 1); UltraMax chart fit as colour proxy, on the camera since v5 [measured for UltraMax, proxy flag] |
| 4 | Sunset | **Phoenix II** (Phoenix 200 option) | unchanged from v5: `1082,47,-92 / 102,1150,-232 / 54,74,890` @`+0x90` | 1037 / 1020 / 1018 | unchanged (`+0x160`, markers `-128` untouched) | **-3 -> k0** | 0 | -1 | Phoenix II scans, boost 1.14 [measured, residual 4.4 dE]; tone from scan black 0.110 / white 0.895 |
| 5 | Black & White | **Acros** | stock slot 5 kept: `1292,-180,-88 / -44,1340,-272 / -24,-108,1156` @`+0xa2` (slot **unverified**) | 1024 x3 | n/a | **+1 -> k4** | n/a (no BKID) | +1 | Fuji Acros, Provia->Acros [measured]; channel-mix matrix is an option (section 3.6) |

Slider bytes (Backup `0x0107xxxx`, 1 byte, attr `0x60`; all 17 are written explicitly because Portrait currently holds the owner's parked `+1 / -1 / -1`):

| slot | contrast ID = value | saturation ID = value | sharpness ID = value |
|---|---|---|---|
| 0 Standard (v1) | `0x01070735` = `01` | `0x01070742` = `01` | `0x0107074f` = `01` |
| 1 Vivid (v2) | `0x01070736` = `fd` | `0x01070743` = `00` | `0x01070750` = `00` |
| 2 Portrait (v4) | `0x0107073a` = `ff` | `0x01070747` = `00` (was `ff`) | `0x01070754` = `00` (was `ff`) |
| 3 Landscape (v5) | `0x0107073b` = `00` | `0x01070748` = `00` | `0x01070755` = `00` |
| 4 Sunset (v10) | `0x0107073c` = `fd` | `0x01070749` = `00` | `0x01070756` = `ff` |
| 5 B&W (v6) | `0x0107073d` = `01` | none | `0x01070757` = `01` |

ID map: BKID triples per style value `v` of `liro_read_creative_style` (C-CTRL-013), with `v = ColorMode + 1` (Standard 1, Vivid 2, Portrait 4, Landscape 5, B&W 6, Sunset 10). **Cross-check [verified-code]:** in the stock snapshot `Backup_post-revert.bin` the only non-zero triple is `0107073a = 01`, `01070747 = ff`, `01070754 = ff`, i.e. v4 = Portrait with the parked +1/-1/-1 (C-BK-012); the B&W and Sepia triples are the only ones without a saturation ID, as expected. Signed bytes: -3 = `fd`, -1 = `ff`, +1 = `01`. The same sliders can be set in the camera menu instead (Menu > Creative Style > each style > Contrast / Saturation / Sharpness).

Block bytes of the colour write (verified against the builder, `+offset` inside `0x30001`/`0x30008`; 64 bytes differ from v5, all in `0x48..0x13f`):

| field | offset | length | bytes (hex) |
|---|---|---|---|
| slot 0 matrix | `+0x48` | 18 | `db 04 87 ff 9e ff c1 ff e0 05 5f fe bb ff 8f ff b6 04` |
| slot 1 matrix | `+0x5a` | 18 | `06 04 54 00 b5 ff 20 00 9e 04 41 ff 0a 00 4c 00 90 03` |
| slot 2 matrix | `+0x6c` | 18 | `7a 04 0a 00 7c ff 35 00 fd 04 ce fe eb ff ce ff 47 04` |
| slots 3, 4 | `+0x7e`, `+0x90` | 18 each | unchanged from v5 |
| hue record r1 | `+0x118` | 24 | `da d9 f6 e4 d9 e0 eb d7 fa 0b cf 16 05 f4 fc fe f2 04 d4 f6 0b f1 00 f2` |
| hue record r2 | `+0x130` | 24 | `d1 dd 03 ec df e9 f1 de f9 0d d7 08 06 f4 01 f8 e8 04 d2 ea 0d ef 00 ef` |

Free read-back of the matrices: the ARW stores the slot matrix of each shot in `SR2:ColorMatrix` exactly (C-COL-007).

---

## 2. How each colour piece was derived

Convention (checked numerically on 2026-10-12): slot matrix = `S(1/boost) . T . M0`, `M0` = stock Standard `1292,-180,-88 / -44,1340,-272 / -24,-108,1156`, `S(k) = k.I + (1-k).1.w^T` (Rec.709 `w`), `T` = look matrix in linear light relative to Standard output, rows sum to 1 (greys keep). `T_house . M0` reproduces House v3 exactly (`1117,-3,-73 / 9,1216,-203 / -16,-11,1022`); `S(1/1.14) . T_phoenix . M0` reproduces Phoenix v3. Magnitude reference: House v3 max element 1216, stock Vivid 1400/-332; the Velvia matrix reaches 1504/-417 (slightly above stock Vivid, see risks).

**Hue records move with their film.** v5 stored Portra's hue edits in slot 1 and House's in slot 2. The film part is `v5 - stock`; it is added to the new slot's *stock* record: `r1 = stock_r1 + (v5_r2 - stock_r2)` (House), `r2 = stock_r2 + (v5_r1 - stock_r1)` (Portra). Without this, House in Vivid would carry Portra's blue-to-cyan push (-31..-38 deg on sky/cyan, E-0017) and break the no-teal rule. Slots 0, 3, 4 records stay as in v5. This transfer is a heuristic [estimate]; hue tables respond up to 1.8x the model (C-COL-023).

### 2.1 Velvia 50 (slot 0) [measured -> fit]
- Source: `~/nex3n-dump/work/filmsim_cmp` (friimaind corpus, 3 pixel-aligned scenes, 1.5 M pixel pairs Provia -> Velvia, SOOC JPEG) plus the abpy-LUT table in `../notes/fuji-film-simulation-research.md` 2c. Provia stands in for Standard (research convention; our base v5+k0 is not Provia, so this transfers character, not pixels).
- Chroma (CbCr) ratio per Lab hue, 35<L<75, 20<C<55: 1.16..1.37 (comparator) vs 1.01..1.41 (abpy, C*=35); the mean of the two per 30-degree bin is the fit target. `film-sim-targets.md` quotes 1.11x: that is the (max-min) proxy, not CbCr chroma. Hue shifts: skin/orange +3..+6 deg, sky/blue +10..+16 deg (both sources agree). Chroma by L band: L<15 x0.86 (clean blacks), L 15..90 x1.2..1.4.
- Neutral tint Provia -> Velvia: |dCb|, |dCr| <= 0.7 code in every Y band, so the neutral axis stays neutral (no LUT tint).
- Fit: 12-hue balanced least squares for `T` (6 DOF, rows sum 1), residual **1.85** (a*,b*) vs 2.80 for a pure scalar `S(k)`; predicted chroma ratio per hue within +-0.07 of target and hue within +-3 deg (hues 210/240 are out of sRGB at the test chroma). Saturation slider +1 carries x1.12 (measured +1 step 43.7 -> 48.1), so the matrix target is the ratio / 1.12. Matrix-only alternative (slider 0): `1371,-213,-134 / -94,1607,-489 / -88,-187,1299` (max element 1607). **[estimate]** for the split between slider and matrix; if red/green patches clip, move more into the slider.
- Tone: Velvia is "deep toe, identity mid, brighter shoulder" (neutral map 16->5, 32->17, 48->39, 64->59, 128->128, 192->188, 240->249 in 8-bit codes). Nearest selectable curve k4 (c+1), RMSE 5.1 codes (k14 4.7 is not selectable in Standard).
- No grain (owner): nothing to do on the colour side.

### 2.2 House 100 (slot 1) [measured]
- `T_house` from `data/looks/v3_looks.json` (refs: 39 scans, k 0.87, no-teal rule, row-sum warmth +1.7 / -0.2 / -2.8 % at boost 1). Re-fit for the Vivid slot boost: `S(1/1.11) . T . M0` = `1030,84,-75 / 32,1182,-191 / 10,76,912` (rows 1039 / 1023 / 998). Boost 1.11 is E-0012 (Vivid chroma above prediction by 11 %).
- Tone k0 (c -3): `notes/tone-curve.md` 4 designed `film_k0` from the same refs (black 0.054, white 0.889 vs refs 0.050 / 0.903). RMSE vs itself 0.
- "Slight grain": DSP-grain track (not colour); would key on the slot byte `[0xc3bad724]` (`../notes/film-presets-plan.md`).
- Known residual (house notes 5): warmth is ~2 b* short of the refs inside the +-3 % row-sum limit; the shared LUT cannot add it (it would warm Velvia and Acros too). If wanted: raise the limit to +-6 % (house notes 5.1) or accept a warm WB.

### 2.3 Portra 400 (slot 2) [measured + estimate]
- Matrix: Maraver SpyderCheckr fit `1146,10,-132 / 53,1277,-306 / -21,-50,1095` (`data/looks/looks_v1.json`), Portrait boost 1.00 (E-0012: Portrait matched prediction 50.3 vs ~51; house notes see +2..+6 %, ambiguous). Residual after the matrix (blue +4.6 deg, cyan +4.5, foliage -10.7, bluish green +13) is what the moved hue record is for; matrix + curve removes about half the film difference (film-colorchecker-tests 0).
- Warm option **[estimate]** (real Portra has warm shadows/mids per the parvec recipe; Maraver's chart is grey-normalised and shows none): `M.diag(1.03,1,0.97)` = `1180,10,-128 / 55,1277,-297 / -22,-50,1062` (rows 1062 / 1035 / 990; expected grey b* about +2). Not in the default block.
- Tone: recipe shape = black lift about 5 %, otherwise identity (derived). No selectable curve lifts the black without compressing the white (k0 does both); k2 (c -1, mild shadow/mid lift, white intact) has RMSE 4.1 against that shape, k0 10.0. Chosen k2 [estimate]. Exact shape = Tier-B option (section 4).

### 2.4 SantaColor 800 (slot 3) [proxy, estimate]
- **There is no SantaColor 800 chart, datasheet or scan**; emulsion origin unknown (sellers: "process like Portra 800", search snippets only). Colour proxy = UltraMax 400 chart fit (already the v5 Landscape matrix, boost 1.14, verified on camera). Alternative if the "Portra 800" claim is believed: spektrafilm shape `1340,-108,-208 / -60,1272,-188 / -20,-21,1065` x `S(1/1.14)` = `1205,14,-195 / -23,1225,-177 / 12,90,922` (model "direction labels", not truth).
- Tone: contrast 0 (native Landscape k14, S-curve). The UltraMax recipe curve has a small toe dip and 5 % black lift; k14 matches the dip direction, RMSE 5.4 (k2 5.3, identity 3.6 is not selectable here). "Grainy 800" = grain track, plus the recipe family has the strongest grain of the lineup stocks (derived, relative).

### 2.5 Phoenix (slot 4) [measured scans]
- Matrix and hue record stay as v5 (Phoenix II from 24 scans: blues/violets chroma x1.2, reds +8 deg, magenta +10 deg, greens -6 deg; residual 4.4 dE, magenta 10.9, blue 9.0). Do not combine with `v6_phoenixsky`/`v6_kodakwarm` (C-SAFE-002).
- Tone k0 (c -3): scans have black 0.110 / white 0.895 (house notes 2); k0 gives 0.054 / 0.889, the closest selectable. At c 0 Sunset's k14 *deepens* blacks (house notes 5), which is the wrong direction. Whether contrast -3 in the Sunset style behaves like Standard c -3 is untested.
- White balance: Phoenix II scans are neutral-cool; Sunset in **Auto WB** multiplies R x1.40 / G x1.07 / B x0.62 (C-COL-029/030), greys go b* +20, i.e. a warm "Phoenix 200 (I)" look. Fixed WB (Daylight) = the scanned Phoenix II. Both are legitimate; the slot cannot hold both.
- Sharpness -1: the Phoenix recipe is soft (Clarity strongly negative); only measured-source hint, [estimate].

### 2.6 Acros (slot 5) [measured]
- Provia -> Acros (comparator): output chroma exactly 0; neutral tone `0->4, 16->14, 32->28, 48->42, 64->59, 96->94, 112->109, 128->128, 160->162, 192->192, 224->224, 240->243, 255->253` (black lift +4, toe -2..-5, upper mids +2). Selectable fit: k4 (c+1) RMSE 2.2, identity k3 2.7 (B&W's own c0 curve is unknown), k14 2.3.
- Channel mix (gamma domain, luma weights R/G/B): Acros .227/.602/.164, Acros+Ye .412/.552/.027, Acros+R .591/.485/-.089, Acros+G .104/.723/.158, Monochrome .228/.672/.105, versus Rec.601 .299/.587/.114. Fitting a look matrix to the Acros luma lowers the luma error only from 3.1 to 2.7 codes (tone, not mix, is most of Acros), so **the stock slot-5 matrix is kept** (also because slot 5 may not be the B&W matrix, experiment M-2). Option `948,253,-177 / -21,1287,-242 / 41,-89,1072` (R weight down, B up) only if M-2 confirms the slot.
- B&W-specific handling: no saturation write; neutral axis of the shared LUT must stay 0 (it does: node `Cb4,Cr4` of every plane and Y keeps the stock byte); optional filter variants = other matrices (weights above).

---

## 3. Chroma-by-luminance LUT (Backup `0x00030004` and `0x00030005`, written identically)

Geometry [verified-code C-COL-026, verified-hw E-0067]: 1215 data bytes + 65 tail bytes (stock tail zero, never touched). Byte offset of a node = `plane*405 + Ynode*81 + Cb_idx*9 + Cr_idx`; planes: 0 = dY (untouched here), 1 = dCb [inferred: the stock pattern shrinks Cb at Cb=+-128 only in this plane], 2 = dCr [verified-hw: +63 at `1012` reddened the wedge]; Y nodes = Y' 0, 64, 128, 192, 256; Cb/Cr node coordinate = (idx-4)*32 chroma codes. Stock neutral nodes (`Cb4,Cr4`) are 0 at every Y; the stock LUT is a gamut-edge chroma shrink (values up to -55 at the highlight corners).

Calibration [measured, E-0067 + `+dCr` arithmetic]: +63 units at the neutral node, Standard, Y'~134 -> +13.9 a*; at mid grey 1 Cr code = 0.93 a* and 1 Cb code = -1.1 b* -> **1 LUT unit ~ 0.237 chroma code** (effective Level ~2-3 of 8, E-0067 caveat). Per-style gain relative to Standard: Vivid 0.91, Portrait 0.73, Landscape 0.85, B&W 1.33 (one session, one chart). So the largest shift one node can make is +-15 codes (+-14 a*/b*): ample for tints (a few codes), limited for strong desaturation of saturated colours (at |c| = 128 at most about -12 %).

### 3.1 Shared design (written)
New node = clamp(stock + delta, -63, 63) (a 7-bit field wraps instead of clamping, so never exceed +-63). `delta` = radial chroma scale per Y node, direction-preserving:
`dCb = (m_Y - 1) * c_Cb / 0.237`, `dCr = (m_Y - 1) * c_Cr / 0.237`, then scaled so that max(|dCb|,|dCr|) <= 60.

| Y node (Y') | 0 (0) | 1 (64) | 2 (128) | 3 (192) | 4 (255) |
|---|---|---|---|---|---|
| m_Y **[estimate]** | 0.70 | 0.90 | 1.00 | 0.95 | 0.85 |
| delta on the +Cr axis, c = 32/64/96/128 (units) | -41/-60/-60/-60 | -14/-27/-41/-54 | 0 | -7/-14/-20/-27 | -20/-41/-60/-60 |
| effective chroma factor at c = 32/64/96/128 | .70/.78/.85/.89 | .90 x4 | 1 | .95 x4 | .85/.85/.85/.89 |

Grounding: House refs vs NEX Standard shadow chroma 4.9 vs 8.5, highlights 4.2 vs 6.0 (house notes 2, 5.3), divided by the matrix k 0.87 -> shadows 0.67, highlights 0.80; mid unchanged. Velvia measured: L<15 chroma x0.86 relative to the rest (clean blacks). The written values are a **compromise** (Velvia keeps highlight chroma: measured about x1.0 at Y3/Y4 vs 0.85-0.95 written). Neutral tint = 0 everywhere (Velvia measured |tint| <= 0.7 code; B&W must stay neutral).

Write map (per block): planes 1 and 2, Y nodes 0, 1, 3, 4 only (Y2 is unchanged), i.e. byte ranges `405-485, 486-566, 648-728, 729-809` (plane 1) and `810-890, 891-971, 1053-1133, 1134-1214` (plane 2); 288 non-zero deltas per plane, **576 bytes** differ from stock per block (68 / 61 bytes hit the final +-63 clamp in `0x30004` / `0x30005`). `0x30004` and `0x30005` differ in 214 stock bytes, so each is built from **its own** stock bytes (`work/bk/00030004_orig.txt`, `00030005_orig.txt`). Plane 0, the 65-byte tail and every neutral node are byte-identical to stock.

### 3.2 What the Sunset slot needs for Phoenix
Sunset (E-0067: delta a* ~0 for the same edit) does not use `0x30004/5`. Candidates (from the dispatcher): (a) block index 2 -> **`0x00030006`** (1280 B, attr `08`, stock all zero, writable like `0x30004`); (b) kind 1 -> the **2-D LUT in `0x00030007`** (1280 B, attr `08`, stock zero; 3 variants x 162 bytes, no Y axis, so no luminance dependence); (c) LUT off for Sunset. Needed: **experiment S-1** (section 9). If (a): Phoenix gets its own full LUT, ready as `00030006_lineup_v7_phoenix_CONDITIONAL.hex`: `m_Y = 0.35 / 0.70 / 1 / 1 / 1` (scan shadow chroma 2.2 vs 8.5) and neutral tints (dCb, dCr codes) Y2 `(0, +2.4)`, Y3 `(+0.7, +3.4)` from the scans' cool-magenta neutrals (a* +1.2 / +2.2, b* -1.4 / -2.3 vs Standard -1 / -1.5) -> LUT deltas `+10` (plane 2, Y2 neutral node, offset `1012`), `+14` (plane 2, Y3, offset `1093`), `+3` (plane 1, Y3, offset `688`). If (b): the 2-D layout (plane order, axis order, which variant is selected) must be decoded first (not analysed); a 2-D table can give Phoenix a per-hue chroma/hue trim but never a shadow/highlight split. If (c): Phoenix keeps matrix + hue record + k0 + WB choice only. In all cases: the Auto-WB warm gain stays the only luminance-independent warmth source in this slot, and the Sunset hue-record marker quads (`-128`) stay untouched.

### 3.3 LUT limits to remember
Per-film split-toning is not possible while the LUT is shared; capacity is +-15 codes per node; Level, ISO and mode dependence of the effective gain are untested (E-0067: ISO 800, one chart); style gain spread +-30 %.

---

## 4. Tone: what is selectable and what a per-film curve would take

Curves (10-bit in/out, encoded domain), selected per slot by the contrast slider:

| in (10-bit) | 0 | 128 | 256 | 384 | 512 | 640 | 768 | 896 | 1023 |
|---|---|---|---|---|---|---|---|---|---|
| k0 (c -3, **film**, flashed) | 55 | 139 | 243 | 362 | 487 | 612 | 730 | 832 | 909 |
| k2 (c -1) | 0 | 140 | 266 | 389 | 509 | 623 | 748 | 875 | 1023 |
| k3 (c 0 identity) | 0 | 128 | 256 | 384 | 512 | 640 | 768 | 896 | 1023 |
| k4 (c +1) | 0 | 104 | 238 | 376 | 515 | 652 | 784 | 912 | 1023 |
| k5 (c +2) | 0 | 82 | 221 | 370 | 519 | 667 | 801 | 923 | 1023 |
| Velvia target (comparator) | 2 | 69 | 235 | 392 | 513 | 629 | 751 | 888 | 1015 |
| Acros target (comparator) | 16 | 112 | 236 | 376 | 512 | 648 | 768 | 896 | 1015 |

RMSE in 8-bit codes against each target shape (k1 / k6 omitted: worse everywhere): 

| target | k0 | k2 | k4 | k5 | k14 (style default) | chosen |
|---|---|---|---|---|---|---|
| Velvia (measured) | 12.9 | 7.4 | **5.1** | 6.6 | 4.7 | k4 |
| House (film_k0 by design) | **0** | 8.6 | 12.7 | 15.0 | 12.5 | k0 |
| Portra 400 (recipe shape) | 10.0 | **4.1** | 5.0 | 7.9 | 5.4 | k2 |
| UltraMax proxy for Santa | 10.3 | 5.3 | 5.1 | 7.6 | 5.4 | k14 (c 0) |
| Phoenix | by scan black/white, not by recipe curve | | | | | k0 |
| Acros (measured) | 11.0 | 5.4 | **2.2** | 5.1 | 2.3 | k4 |

The recipe-curve RMSEs are for the *LR-style* curves (black lift only); the 39-scan references (black 0.050, white 0.903) support k0 for the C-41 stocks. Honest summary: House and Phoenix get a good tone, Velvia/Acros a fair one, Portra/Santa a rough one.

Option, **Tier B, not needed for the Backup-only plan**: bake exact per-film shapes into the unused contrast steps by a narrow p3 write of `k1..k5` (`0x5b006a + 0x800*k`, 2 KiB each, same method as the k0 write C-DLV-010: one precedent, build offline, full gate). Designed 9-knot curves (input 0,128,...,1023): Velvia `[2,69,235,392,513,629,751,888,1015]`, Acros `[16,112,236,376,512,648,768,896,1015]`; Portra/Santa/Phoenix shapes would be built from their recipe curves. Not planned.

---

## 5. Per-film ideal LUT parameters (kept for Sunset / a future per-style selector; NOT written to the shared block)

Units: chroma codes (Cb, Cr) at the Y node; convert with `/ 0.237`. Direction of a recipe tint = YCbCr of its hue; size **[estimate]** (0.15 code per colour-grading saturation unit, no calibration exists).

| film | m_Y (Y0..Y4) | neutral tint (dCb, dCr) per Y node | basis |
|---|---|---|---|
| Velvia | 0.70 / 1.0 / 0.95 / 1.05 / 1.0 | 0 | comparator: L-band chroma, neutral tint <= 0.7 [measured] |
| House | 0.67 / 0.85 / 1.05 / 0.90 / 0.80 | Y1 `-1.8, 0`, Y2 `-2.3, 0`, Y3 `-1, 0`, Y4 0 (residual warmth after the matrix, b* +2..+2.5) | house notes 2, 5 [measured]; Y1/Y3 interpolated [estimate] |
| Portra 400 | shared | Y0/Y1 `(-2.0,+1.0)` warm shadows, Y2 `(-3.1,+2.9)` warm mids, Y3/Y4 0 | recipe shadow tint hue 42, midtone grade hue 28 [estimate] |
| SantaColor 800 (UltraMax proxy) | shared | Y0/Y1 `(+0.5,-0.7)` cool shadows, Y3/Y4 `(-1.5,+2.6)` warm-red highlights | recipe split-tone [estimate], proxy |
| Phoenix II (scans) | 0.35 / 0.70 / 1 / 1 / 1 | Y2 `(0,+2.4)`, Y3 `(+0.7,+3.4)` | scans [measured] |
| Phoenix 200 (I, warm recipe) | as Phoenix II | Y2 `(-10.6,+1.5)`, Y3/Y4 `(-7.6,+1.4)` | recipe highlight/midtone grade hue 59-64, strong [estimate]; contradicts the owner's Phoenix II scans |
| Acros | any | **exactly 0** | B&W must stay neutral |

Tints within +-3 codes can instead be had per slot through matrix row sums (warm: `M.diag(r,1,b)`, r>1>b; effect grows with level, about +1.5 b* per +-3 %). That is the per-slot substitute used for House (+1.7 / -0.2 / -2.8 %), Phoenix (+1.3 / -0.4 / -0.6 %) and the Portra option.

---

## 6. Reversible write and revert (Tier A: Backup attr-08/0x60 writes, updater-shell recoverable)

Rules (05 section 4): never touch `0x00030002`, `0x00bc*`, `0x0132*`, calibration blocks, `0x00030056`, `0x00030024`, `0x0003004c`, `0x00FA0080`, `0x00bd*`. Written here: `0x00030001`, `0x00030008`, `0x00030004`, `0x00030005`, 17 slider IDs `0x0107xxxx`; later (conditional) `0x00030006`. No twin banks exist for `0x30004/5` (they are separate blocks written identically, as in E-0067).

Preconditions: charged battery, Power Save 30 min, `pkill -9 -f ptpcamerad`, USB = Mass Storage, camera on `current_p3` (restore-first), session start via `~/nex3n-dump/work/pmca/session.sh`.

1. **Snapshot (the revert source).** Read every ID to be written and save raw: `0x00030001`, `0x00030008`, `0x00030004`, `0x00030005` (+ `0x00030006`, `0x00030007` for S-1), the 17 sliders; plus a whole-Backup snapshot `~/nex3n-dump/Backup_pre-lineup.bin`. Compare before writing: `0x30001/0x30008` must equal `work/bk/00030001_looks_v5.hex` (md5 of the hex file `9e3fc4ac...`), `0x30004/5` must equal `00030004_orig.txt` / `00030005_orig.txt` (E-0068 reverted the EXP-2 byte; md5 `c0f43074...` / `217e2d33...`), the 17 sliders as in the 04.10 snapshot (`00` except `073a=01, 0747=ff, 0754=ff`; a different slider value is not an error, the owner may have changed it in the menu, just record it). Any deviation in the colour or LUT blocks: **stop and diff**, do not write.
2. **Write**, in this order: `0x30001`, `0x30008`, `0x30004`, `0x30005`, then the sliders; `saveBackup`; read back every ID and compare byte for byte; reboot (C-BK-002/003 disagree on immediate effect).
3. **Verify** (section 8). 
4. **Revert** = write the saved raw blocks back (steps 1-2 reversed), `saveBackup`, read back, reboot. Fallbacks: the same values from `work/bk/00030001_looks_v5.hex`, `*_orig.txt` and the slider list above; whole-file `Backup_pre-lineup.bin` via `bk patch` only as a last resort (rewrites the whole Backup, E-0002).

Senser form (template modelled on the proven `work/filmgrain/deliver_setting.py`, which did `writeBackup` + `saveBackup(0)` + read-back on `0x00bd0002`; **not yet logged for `0x0003xxxx` blocks**, those were written through the updater shell `bk w/s` in E-0010..E-0020 and E-0067, so run the first block with read-back and fall back to the shell form if senser refuses):

```python
# senserShellCommand(complete=go)  -- same imports/libusb shim as deliver_setting.py; define HOME and PRE (snapshot dir) first
def tok(p): return bytes(int(x, 16) for x in open(p).read().split())
NEW = HOME + '/nex3n-dump/work/bk/lineup_v7/'
W   = {0x00030001: NEW + '00030001_lineup_v7.hex', 0x00030008: NEW + '00030008_lineup_v7.hex',
       0x00030004: NEW + '00030004_lineup_v7.hex', 0x00030005: NEW + '00030005_lineup_v7.hex'}
SL  = {0x01070735: 0x01, 0x01070742: 0x01, 0x0107074f: 0x01,            # ... all 17 from section 1
       0x01070747: 0x00, 0x01070754: 0x00}
def go(cam):
    for i in list(W) + list(SL):                       # 1) snapshot = revert source
        open(PRE + '%08x.bin' % i, 'wb').write(cam.readBackup(i))
    cam.setBackupId1(False)                            # as in the proven script
    for i, p in W.items():  cam.writeBackup(i, tok(p))
    for i, v in SL.items(): cam.writeBackup(i, bytes([v]))
    cam.saveBackup(0)
    for i, p in W.items():  assert cam.readBackup(i) == tok(p)
    for i, v in SL.items(): assert cam.readBackup(i) == bytes([v])
# revert: identical loop with data = open(PRE + '%08x.bin' % i, 'rb').read()
```

Updater-shell form (proven path): `bk r 00030001`, `bk w 00030001 <1536 hex tokens>`, same for `00030008`, `bk w 00030004 <1280 tokens>`, `00030005`, `bk w 0107073a ff`, ..., `bk s`.

Safer staging (recommended): **stage 1** = matrices + hue records + sliders only (skip the LUT), shoot the chart in all six slots, compare `SR2:ColorMatrix`; **stage 2** = LUT; each stage has its own snapshot and revert.

---

## 7. Risks of the design (tune-on-camera list)

1. Velvia matrix G-row `1504 / -417` is above stock Vivid (`1400 / -332`): saturated greens may clip earlier. Fallback: saturation slider +2 (about x1.25; sets `0x01070742 = 02`) with the milder matrix `1131,-44,-63 / -38,1411,-349 / -52,-50,1126` (fit residual 1.5; max element 1411, same as stock Vivid).
2. Chroma boosts per style (1.11 / 1.14 / 1.00) are disputed (C-COL-012: SIM fit x1.06 / 1.11 / 0.96 / 1.07). A wrong boost shows as a chroma offset of the whole slot, fix by one `S(k)` factor.
3. Hue-record transfer between slots is a heuristic; check House's cyan/blue hue (no-teal) and Portra's skin hue on the chart first.
4. LUT unit (0.237 code) and style gain spread come from one session; m_Y values are estimates. Effect on greys must be exactly zero (verify).
5. Standard (slot 0) is likely also what the camera forces in automatic/scene modes [hypothesis]: Velvia saturation and k4 contrast would apply there too.
6. Contrast -3 on Vivid and Sunset (curve k0) is untested; only Standard c -3 was measured (C-TONE-011).
7. Session drift is large (C-COL-042): every comparison needs a same-session baseline.

---

## 8. Verification plan (after each stage, same light, same session, Daylight WB, P/A/S/M)

- Matrices: one RAW+JPEG per slot; `SR2:ColorMatrix` must equal the table (free exact check).
- Neutral axis: 21-step grey wedge per slot (`code/measure/ramp.py`): after stage 2 |a*|,|b*| differ from the stage-1 frame by <= 1 at every step (LUT must not tint greys; B&W a* stays 0.000).
- Tone: wedge Y' per slot against the chosen k (section 4); Velvia/Acros toe deeper than Standard c0.
- Chroma by luminance: ColorChecker (or a saturated chart) before/after stage 2: dark saturated patches chroma x0.8..0.9, mid patches unchanged (+-3), light patches x0.9..0.95.
- Per film: Velvia vs the comparator Velvia frame on the same scene type (hue/ratio table of 2.1); House and Phoenix vs `house-phoenix-looks.md` section 4 predictions; Portra skin hue; Santa: record as proxy only.

---

## 9. Open items and the experiments that close them (Tier A, Backup only; write hypothesis and predictions before running)

| id | question | edit | predicted outcomes | revert |
|---|---|---|---|---|
| **S-1** | Which block/path does Sunset use? | `0x30006` byte `1012` = `3f` (plane 2, +dCr, a* signature) **and** `0x30007` bytes `40, 121, 202, 283, 364, 445` = `3f` (neutral node of both planes of each of the 3 two-D variants; layout unknown, any response counts) | Sunset grey wedge: a* up -> block 6 (3D, index 2); any cast from `0x30007` -> 2-D path; no change -> LUT off for Sunset | all written bytes back to `00` (both stock blocks are all zero) |
| **M-1** | Do `0x30004` and `0x30005` serve different style classes? | `0x30004` byte `1012` = `3f` (plane 2, +dCr), `0x30005` byte `607` = `3f` (plane 1, +dCb) | per style: a* up = block 4, b* down = block 5, both/none = see S-1 | bytes back to `00` |
| **M-2** | Is slot 5 (`+0xa2`) the B&W matrix, and does B&W luma follow it? | slot 5 = R-heavy matrix (e.g. `Acros+R` mix) | B&W frame of a red patch changes tone -> slot 5 confirmed | stock slot-5 bytes |
| **P-1** | Does Contrast -3 / +1 select k0 / k4 in Vivid, Sunset and B&W like in Standard? | sliders only (part of stage 1) | wedge matches k0 / k4 | slider bytes |
| **L-1** | LUT only in P/A/S/M? ISO dependence of the LUT gain? | shared LUT, wedge at ISO 100/800/3200 and in iAuto | greys untinted; chroma factors constant | stage-2 revert |

Registered as candidate claims for 02/07 when run: dispatcher selector decode (section 0), 3D LUT shared across styles (E-0067 + decode), `0107xxxx` slider ID map (verified against the stock snapshot), Create3DLUT unit calibration.

---

## 10. Rename of the six style labels (research only, nothing edited)

**Where the names live [verified-code]:** not in av-cam and not in `/setting`. The UI strings are records in `/usr/share/app/string_<language>.uxc` inside partition **p8** (`/usr`, ext2 inside an LZPT stream; unpacked copy `~/nex3n-dump/safeboot/out3n/nflasha8_unpacked_unpacked/share/app/`). The language -> file table is in `global.xdb` (`RES_NS_STRING` banks); `libObj.so` holds the path prefix `/usr/share/app/`. The Creative Style menu (`viewUnified2.so`, item table `0x656d4`, item = 0x28 bytes, string id at `+0xc`; hidden-styles.md) references these English records:

| style | string id | record offset | capacity (chars, in place) | proposed | fits |
|---|---|---|---|---|---|
| Standard | `0x126` (**shared** with JPEG quality "Fine / Standard"; `0x127` "Standard" is used in `viewUnified4` and next to "Wide") | `0x3320` | 11 | `Velvia50` (8) | yes, but also relabels the quality setting |
| Vivid | `0x146` | `0x34bc` | 7 | `House` (5) | yes |
| Portrait | `0x147` | `0x34c8` | 11 | `Portra400` (9) | yes |
| Landscape | `0x148` | `0x34d8` | 11 | `Santa800` (8) | yes |
| Sunset | `0x149` | `0x34e8` | 7 | `Phoenix` (7) | yes, exactly |
| Black & White | `0x14a` | `0x34f4` | 15 | `Acros` (5) | yes |

Also exist: a second 16-name table `0x61..0x70` (Standard, Vivid, Neutral, Clear, Deep, Light, Portrait, Night Scene, Sunset, Autumn leaves, Sepia, Landscape, ..., Black & White, Sepia) with 32-bit references in `libObj.so` (hits `0x61` x40, `0x62` x9, `0x67` x10, `0x6c` x9, `0x6f` x5; which screens use it is not established), `viewUnified4.so` (Fn / Quick Navi list: `0x126 0x127 0x146..0x14a` plus title `0x145`), and the **Scene Selection** strings `0xea/0xed/0xee` and `0x640/0x643/0x644` ("Portrait", "Landscape", "Sunset") which must NOT be renamed. av-cam has only internal colour-mode names (15 strings at `0x3d72d4` and a copy at `0x3d9204`, e.g. "Vivid", "Nightview", "BW", no "Black & White") used by the colour module for the EXIF mapping, not the UI (searched: av-cam, libObj, viewUnified2/4, p8 `share/app`, `global.xdb`; **not searched**: whether libObj can load an override resource from `/setting` or the card - the only path literal found is `/usr/share/app/`).

**Feasibility.** Record format is understood and tooling exists: `[u16 id][00][1e] UTF-8 \0`, 4-byte aligned, u16 word-offset table, no checksum; `work/make_p8_mod.py` already built an in-place same-length edit ("Sunset" -> "House ") where the ext2 image differs by 16 bytes and **two** LZPT blocks (191, 192) recompress to the same size, so a minimal in-place delta exists (`work/mod/`, `SHA1SUMS`). Caveats: (1) that old test build replaced **all four** "Sunset" records, including Scene Selection; a correct build edits only `0x149` (+ whichever of `0x61..0x70`/`0x127` turn out to be displayed); (2) `0x126` needs either accepting the relabelled JPEG-quality entry or repointing the menu item's string id; (3) only the **active UI language** file matters (an English capacity table is above; the Russian file is 341 KB and needs its own capacity check); (4) UTF-8 for non-ASCII.

**Reversibility.** The edit is same-length and checksum-free and the original p8 stream is on disk (`nflasha8` md5 `0e1fd3d0eabaf2d93f502982b374c825`), so reverting is rewriting the two blocks. But p8 is **Tier C (forbidden by the owner's rule)**: if an edited p8 failed to boot, recovery is disputed in the atlas (C-SAFE-005 "only by opening the camera" vs C-SAFE-006 "repairable from the updater, which lives on p1") and has never been tested. Verdict: renaming is **feasible in principle, reversible only if p8 still boots, and not recommended under the current tiering**; the labels stay Standard/Vivid/Portrait/Landscape/Sunset/B&W and menu order = slot order. Nothing was written or built for this page.

---

## 11. Provenance of the numbers

| number | source |
|---|---|
| stock matrices, M0, slot offsets, hue records, 3D LUT geometry, slider IDs | atlas 02 (C-COL-002/003/005/013/026/046), 03 (C-CTRL-013, C-BK-012), stock dump `~/nex3n-dump/work/bk/`, snapshot `Backup_post-revert.bin` |
| House / Phoenix `T` and boosts | `data/looks/v3_looks.json`, `notes/house-phoenix-looks.md`, E-0012 |
| Portra / UltraMax / SF-CA2 matrices | `data/looks/looks_v1.json`, `slot_candidate_matrices.json` (Maraver charts, spektrafilm) |
| Velvia / Acros tone, chroma, channel mix | `~/nex3n-dump/work/filmsim_cmp` images, this pass (`/tmp` scripts folded into `build_lineup.py` for the fit; measurement tables above) and `notes/fuji-film-simulation-research.md` 2a-2d |
| LUT unit, style gains | E-0067 (+13.9 / 12.7 / 10.1 / 11.8 / 18.5 a*), Lab arithmetic at Y'=134 |
| tone curves | `sys_avcam.bin` `0x5b006a + 0x800*k` (k0 = flashed film curve), C-TONE-002/010 |
| dispatcher / selector decode | capstone sweep of `sys_avcam.bin`: `0x3d12f8`, `0x2ea930`, `0x2eac72`, `0x2eb038` (2026-10-12) |
| string records | `string_english.uxc` parse (format of `work/make_p8_mod.py`), `hidden-styles.md` |
| recipe-derived directions and shapes | parvec pack, local only; derived values only |
