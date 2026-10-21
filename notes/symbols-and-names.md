# NEX-3N: av-cam symbols, Backup 0x0003 names, who reads colour and tone

Static analysis of files only. Nothing written to the camera. Addresses are **file offsets in the 3N `av-cam` binary** (VA = `0xc3441000` + offset; RW data: VA = offset + `0xc3682120`). Tags: **[code]** = read in the disassembler; **[port]** = carried over from the DSC-HX20; **[hypothesis]** = inference not verified on camera. Related: notes/prior-art.md, notes/backup-params.md, notes/tone-curve.md, notes/sa-interface.md, README.md.

Working artefacts (not included in this repo): a 3N symbol map (224 rows: address, offset, name, confidence, method), a role list for 0x0003 blocks and neighbouring BKIDs, and porting scripts. The porting reference is the HX20V 1.01 `av-cam` whose md5 (`8f01aeb5...`) is exactly the one the ma1co OpenMemories-Symbols names were written against. Also used: clones of `OpenMemories-Symbols`, `OpenMemories-Platform`, `steelcnn/nex-hack`.

## 0. Summary

1. **Symbols ported: 202 names of 218, 181 with high confidence.** Three independent methods:
   - av-cam service "veneers" (uITRON, OSAL, `Backup_*`, 106 of them) matched by slot number in the service table; **names of all slots taken from `liro.ko`**, whose `.rel.init.data` is the same table in the same order (`CRE_TSK`...`cache_inv_range`). Slot shift is constant (+0x24), all 96 HX20 veneers matched [code];
   - tasks via the task-creation table (id + priority + stack), 46 of 51 fully matched;
   - interrupts via their number in the table.

   `Backup_read` = `0xc3676ab3`, 1050 calls. `Backup_read_multi` = `0xc3676af9`, `Backup_reg_cb` = `0xc3676bfb`, `Backup_write` = `0xc3676b8d`.
2. **The NEX-6 IDA database (`steelcnn/nex-hack`) is useless for names.** 9412 `MakeName`s, of which three are meaningful; the rest are IDA auto-names (`jpt_`, `nullsub_`).
3. **Colour block `0x00030001` is loaded once at boot but updated live** [code]:
   - `bk0003_cache_init` (`0x1819cc`, called at boot from `fn_7c18`) registers `Backup_reg_cb` on all 180 IDs of subsystem 0x0003. Callback `0x1819a2` `memcpy`s new data into the RAM copy on any write to an ID;
   - the block itself is read by one `Backup_read_multi` (`0x18183e`) into RAM `0xc3ac2b94`;
   - per frame, four colour-parameter builders (`0xc60c6`, `0xc6430`, `0xc6b12`, `0xc7452`; the last called from `ExtractCaptureData`) place a **pointer** to the RAM copy into a struct: `0x30001` or bank `0x30008`.

   Hence `bk w 00030001` takes effect from the next frame without a reboot, which explains why our experiments applied immediately [code; matches experience].
4. **Style tone-curve selection** [code]:
   - path: menu `0x01070175` -> `liro_read_creative_style` (`0x2a0f2a`) -> camera parameter `0x4039` (variable `0xc3abe32c+4`) -> ... -> param struct field `+0x4f` (curve index) and `+0x48` (enable) -> `0x2d7e38`/`0x2d7f88` copy them to `obj+0xbe1`/`obj+0xbd5` -> `tone_lut_build` (`0x2d6996`) takes the curve from table `0xc3cb68a0[idx]`;
   - the link "colour mode -> curve index" (between `0xc3abe32c` and `+0x4f`) is **not found**.
5. **New: Backup contains a debug tone switch, `0x0003007a+0xD7`** [code]. Default 0. Values:
   - **1**: the 96-point Y tone LUT is taken **directly from `0x3007a` u16[0..95]**, 9 segment parameters from `+0xC0`;
   - **2**: curve indices are forced from Backup (`+0xD9` base, `+0xDB` contrast, `+0xDD`, `+0xDF`, **`+0xE5` style curve**, `+0xE7`);
   - **3**: dump of the hardware LUT to RAM.

   This **corrects notes/tone-curve.md**, which said tone cannot be changed through `bk w` and that `0x3007a` is the X grid. Per code: in normal mode `0x3007a` is unused; in mode 1 it holds **Y values**. Not verified on camera (section 3).
6. **Sunset warmth under AWB not found in code.** No AWB strings in av-cam; the "colour mode -> AWB" chain was not traced in time. Open (section 4; see also notes/open-questions.md).
7. **The PMCA-RE #233 technique does not apply to subsystem 0x0003.** Userland (`libObj`, `libmprctrl`, all `.so`) has no PARAM_ID -> BKID tables for 0x0003. The subsystem lives only inside av-cam, and the firmware contains no Sony names for its blocks. The role list therefore holds **our roles** derived from code and experiments, plus 51 string hints for neighbouring subsystems (e.g. `0x0092001f` = `BKID_UPM_DEBUG_DISLABLE_DFS_TRANS`, `0x00560001...7` = `BKID_SDF_QTBL_*`).
8. **a7 IV Creative Look not covered here** (see notes/open-questions.md section 1).

## 1. Symbol porting

| Group | Matching method | Count | Confidence |
|---|---|---|---|
| ORIL header (`entry_pre/main`, `suspend`, `resume`, `exit`, `func1..3`, `reset`) | header layout identical on HX20 and 3N (`ORIL`, version 4), pointers read directly | 10 | high |
| Service veneers (uITRON, OSAL, Backup, cache, memcpy) | emulate veneer -> slot offset in `*(base+0x14)`; name via HX20 and via `liro.ko .rel.init.data` (slot - 0x24) | 106 | high; 96/96 matched on HX20 |
| Tasks `tskNN_*` | task-creation table in `.data` (0x9c-byte element, `[entry, prio, stack, ..., id@+0x4c]`), match on id, prio, stack + code similarity | 51 | 40 high, 7 medium, 4 low (`tsk49_sio`, `tsk56_accy`, `tsk63_cpu_selector`: different priority, dissimilar code) |
| Interrupts `intNN_*` | table `(intno, 0, handler, 1)` | 46 | 37 high, 9 medium |
| `cyc1_adc` | unique 16-byte signature | 1 | medium |
| Own names from this analysis | manual, sections 2-3 | 21 (+ section header) | "analysis" |

The 3N has veneers the HX20 does not use. Per `liro.ko`: `Backup_nread*`, `Backup_sync_subsystem`, `dmm_direct_call`. Full Backup API in `liro.ko`: `nread`, `read_setting_attr`, `get_datasize(_multi)`, `get_attribute`, `read(_multi/_async)`, `write(_vsize/_multi/_async)`, `sync_subsystem/all`, `reg_cb/unreg_cb`, `reset(_subsystem/_all)`, `check`, `read_4Byte`.

## 2. Who reads `0x00030001` and when [code]

- **Boot cache.** The 180-ID list is at `0x61d1dc`, an alternative list at `0x61d4b0`, the RAM-address list at `0x61d784`.
  - The alternative list differs in 38 bank-B IDs: `0x3000c...18 -> 0x300b0...bc`, `0x3001a/1b -> bd/be`, etc., as in notes/backup-params.md.
  - Loader `0x18183e` uses the alternative list if `[0xc3c9f2dc+0xc]==1 && [0xc3c9f2dc]!=0`. Callback registration (`0x1819cc`) always uses list A, because the flag has just been cleared there.
  - `0x30001` -> RAM `0xc3ac2b94`, `0x30008` -> `0xc3ac4894`. Both are in list A as separate blocks: not an A/B bank pair but two colour blocks.
- **Update.** Callback `0x1819a2` = `memcpy(dst, src, size)` into the same RAM copy plus a log line. Separately, `0x181f4a` re-reads one ID on request (ID 0 = all).
- **Consumption.** Four builders put a **pointer** to the block into the first field of the parameter struct. Choice of `0x30001` vs `0x30008`:
  - `0xc60c6`, `0xc6430`, `0xc7452`: bank `0x30008` if `ctx[1]->+0x14 == 1`;
  - `0xc6b12`: same choice via `[0xc3cab360+3]` (`0xc6430` stores this flag there).

  Callers: `ExtractCaptureData` (`0x2e8820`, every frame), 18 per-shooting-mode functions (`0x2e8896...0x2e93f0`), plus `0x2b1b4` and `0x2b01e` (probably monitor and preview [hypothesis]).
- So **ARM neither caches nor copies the matrices**: the slot (`+0x48+18*slot`) is selected by whoever reads the struct downstream, probably DSP/HAPI, since no ARM access to `+0x48` from this pointer was found [hypothesis]. What flag `+0x14` means (when bank `0x30008` is active) is not established. Both banks are identical in stock, so keep writing both.
- **False references.** Literal `0x00030001` appears dozens more times in av-cam as a **message or parameter identifier** (`fn_29d134(0x30001, ...)` when sending a style), not as a BKID. Context-free literal search is misleading.

## 3. Tone: where the style curve is selected, and debug mode `0x3007a`

**Normal path** [code]:
1. `liro_read_creative_style` (`0x2a0f2a`) reads `0x01070175` (byte 0 = menu item; currently `02`). A jump table selects the "contrast / saturation / sharpness" BKID triple for that style:

   | v | contrast | sat. | sharpness |
   |---|---|---|---|
   | 1 | 0x0107**0735** | 0742 | 074f |
   | 2 | 0736 | 0743 | 0750 |
   | 3 | 073e | 074b | 0758 |
   | 4 | 073a | 0747 | 0754 |
   | 5 | 073b | 0748 | 0755 |
   | 6 | 073d | - | 0757 |
   | 7 | 073f | 074c | 0759 |
   | 8 | 0740 | 074d | 075a |
   | 9 | 0741 | 074e | 075b |
   | 10 | 073c | 0749 | 0756 |
   | 11 | 0737 | 0744 | 0751 |
   | 12 | 0738 | 0745 | 0752 |
   | 14 | 0739 | - | 0753 |

   13 styles; v=6 and v=14 have no saturation, apparently B/W and Sepia [hypothesis]. Other number-to-style mappings are not established; Standard is probably v=1 [hypothesis]. Hidden styles are fully present here; the filter sits in the menu (consistent with README).
2. `menu_style_to_colormode` (`0x29dd1a`) maps v to colour mode v-1. The mode is sent as parameters `0x4039` (mode), `0x403a/b/c` (sliders). Handler `0x20fde` stores them at `0xc3abe32c+4/+8/+9/+0xa`.
3. ... (how the mode becomes a curve index was not found) ...
4. `0x2d7e38` (monitor) and `0x2d7f88` (capture) copy from the param struct:
   - `+0x48` -> `obj+0xbd5` (enable style curve);
   - `+0x4f` -> `obj+0xbe1` (index into `0xc3cb68a0`, i.e. slots 14...26 from notes/tone-curve.md);
   - `+0x4c` -> `obj+0xbdb` (contrast 0...6);
   - `+0x4a` -> `obj+0xbd9` (base);
   - `+0x4d` and `+0x4e` -> k7...13 family and another index.
5. `tone_lut_build` (`0x2d6996`) computes 96 Y values via the chain "base -> contrast -> k7 family -> style". `0x2d6ba8` builds the X grid.

**Debug mode via Backup** [code, not verified on camera]. Byte **`0x0003007a+0xD7`** (currently `00`) is copied to `obj+0xbe2` and sets the mode:
- **1**: after the normal computation, `0x2d8644` (capture) or `0x2d676e` (monitor) **overwrites the 96 LUT values with `0x3007a` u16[0..95]**, and the 9 segment params from `+0xC0`. The result then goes to hardware (`fn_37ddc8`/`fn_37d6ec`). The same `0x2d8644` is the fallback if the normal computation returns an error.
- **2**: curve indices come from Backup:
  - base `+0xD9`;
  - k7 family `+0xE7`;
  - contrast `+0xDB` (+ enable if != 3);
  - `+0xDD`, `+0xDF`;
  - **style curve `+0xE5`** (enabled if != 0).
- **3**: hardware LUT (`0xf4015300`) copied to RAM (diagnostics).

Implications:
- **Mode 1 = a global tone curve via `bk w`.** It is shared by all styles and **replaces the whole chain including base gamma**. Stock `0x3007a` = `2,4,...,1023`, i.e. Y = X: mode 1 without custom numbers would probably give a linear (dark, contrasty) frame [hypothesis].
- For a custom film curve, Y must equal `base(film)` at the X grid nodes. The grid is built by `0x2d6ba8`; in stock the nodes coincide with the current `0x3007a` values [hypothesis from the match with `+0xC0` = `2,2,3,4,4,4,4,3,3`].
- **Mode 2** lets any **stock** curve be applied to all styles at once. Style indices and the correct route to k0 (via contrast, not style) are analysed in section 7.
- This contradicts notes/tone-curve.md section 0.4 that `0x3007a` goes to hardware as breakpoints. Per code it goes there **only in mode 1, and as Y**. The "null test" proposed there (edit `+0x00...0x3f` in mode 0) should indeed yield nothing, but for a different reason.

## 4. Sunset warmth (AWB) - open

- Known from experiments: on Auto WB, Sunset greys shift by b* +20; no shift at fixed WB.
- av-cam has no `AWB` strings. WB strings relate only to the panel and EVF (`ADJ_CMD_AVBB_*`) and to `PBEH:wb_r/b`.
- `YC_SetModeDependent_Sunset` (`0x464daa`) writes Apacon registers `0x78b0...0x78bf` (sharpness), not WB.
- The colour mode lives at `0xc3abe32c+4`. Readers of this whole struct: `0x2001a` (`fn_1feec`, group copy) and `0x2217a`. AWB probably goes through them too [hypothesis]. Next step: follow `fn_1feec` to the AWB struct.
- `0x30001` itself contains 8-byte record pairs with correction-like values: `+0x2aa...0x2e7`, `00 00 0a f8 07 e8 c6 ad / 00 00 17 f7 08 ee 42 53`, last slots `e9 e6 / 23 2c`. Possibly per-style corrections, not necessarily WB [hypothesis, not confirmed by code].

## 5. Next (by value)
1. **On camera:** test mode 1 on `0x3007a` (see section 8 for the computed values).
2. Trace the missing link "colour mode (`0xc3abe32c+4`) -> `+0x4f` / matrix slot", readers `0x2001a`/`fn_1feec`. This would also expose the AWB warmth.
3. Load the symbol map into Ghidra (import names by VA/name columns) and work with names.

## Sources
- github.com/ma1co/OpenMemories-Symbols (`known_files.yaml`, DSC-HX20 1.01), github.com/ma1co/OpenMemories-Platform (`stubs/backup.S`, `drivers/backup.h`), github.com/steelcnn/nex-hack (`av-cam-NEX6-v1.01.idc.zip`), github.com/ma1co/fwtool.py PR #52 and #53, github.com/ma1co/Sony-PMCA-RE issue #233.
- HX20V firmware 1.01 (official Sony update).
- Own data: 3N `av-cam` (md5 `d0003041...`), `liro.ko` from initrd, rootfs, a Backup export.

## 7. Tone mode 2 (`0x0003007a+0xD7 = 02`): analysis before the experiment

Everything here is **[code]** (functions `0x2d7e38` monitor, `0x2d7f88` capture, builder `0x2d6996`) unless tagged otherwise. Not verified on camera.

### 7.1 Which bytes set what
Block `0x0003007a` (256 B, attr `08`, **single bank**: not in the bank-B list). The override fires only if `+0xD7 == 2`. Each byte is applied **only if within its valid range**; otherwise the value from style and menu remains. The override only **sets** enable flags to 1, never clears them.

| Byte | Destination | Range | Selects | Side effect |
|---|---|---|---|---|
| `+0xD9` | `obj+0xbd9` | < 0x1C | base gamma: row of table `0xc3cb6788` (28 x 2 pointers) | - |
| `+0xE7` | `obj+0xbd6` | < 2 | base gamma column (0/1) | - |
| `+0xDB` | `obj+0xbdb` | < 7 | **contrast curve = k0...k6** (slots 0...6 of RW table `0x634748`) | if != 3, sets `obj+0xbd1 = 1` (contrast on) |
| `+0xDD` | `obj+0xbdd` | < 7 | k7...k13 family (slots 7...13) | if != 3, sets `obj+0xbd3 = 1` |
| `+0xDF` | `obj+0xbdf` | < 6 | another group: table `0xc3c10b9c` (bss, filled at runtime; 7 = "none") | sets `obj+0xbd3 = 1` |
| `+0xE5` | `obj+0xbe1` | < 0x0E | **style curve**: slot 14 + idx | if != 0, sets `obj+0xbd5 = 1` |

**Correction to the slot table in notes/tone-curve.md:** per the pointers in RW table `0x634748`, slots 14...27 = `k20, k14, k15, k16, k17, k18, k20, k19, k20, k20, k20, k20, k20, k20` (k20 = identity). So **style index 0 = k20 (identity), not k0**. Index 1 = k14 (S-curve of Vivid/Landscape/Sunset). **k0 is unreachable via the style index**: it sits only in contrast slots, reachable via `+0xDB = 0`.

**How the builder combines curves.** Stages are **not all composed; one is chosen by priority** (`0x2d6996`, branches `0x2d6a32...0x2d6b30`):
1. if the k7 family is on (`bd3`): `y = contrast[ k7fam[ base(x) ] ]` (or from group `0x1f` instead of base, if set);
2. else if contrast is on (`bd1`): `y = contrast[ base(x) ]`;
3. else if style is on (`bd5`): `y = style[ base(x) ]`;
4. else `y = base(x)`.

So with contrast enabled **the style curve is not applied**. Worth checking against measurements: Vivid at Contrast != 0 should lose its S [menu hypothesis; per code that is the case].

**Global or per style.** Global. The override sits after the style parameters are copied, fires on both paths (monitor and capture), and does not depend on style number. One byte set affects all styles, all contrast slider positions, and live view.

### 7.2 What else mode 2 switches, and what is dangerous
- Mode byte `obj+0xbe2` is read only by tone functions: `0x2d7124` (modes 1/3, monitor), `0x2d79e0` (modes 1/3, capture) and the two override functions (2). Other stages (NR, colour, DRO gains) do not see it. Of other `0x3007a` consumers: `+0xD2...+0xD6`, `+0xE0...+0xE3`, `+0xE6` are read elsewhere, but **we do not change them**. The bytes we change, `+0xD9...+0xE7`, are read only in the override.
- **Base (`+0xD9`/`+0xE7`) is the only dangerous part.** Table `0xc3cb6788` has empty rows: 2, 9, 12, 19...27 entirely; 10...18 lack column 0. Selecting an empty one makes the builder return an error, and the capture path **falls back to the Backup LUT** (`0x2d8644`, same code as mode 1). With stock `0x3007a` numbers that is probably a dark linear frame [hypothesis, 7.4]. So **do not override base: `+0xD9 = FF`, `+0xE7 = FF`** (out of range = leave alone).
- Stock values of these bytes (`00, 03, 03, 07, 00, 01`) **do not mean "change nothing"**. `+0xD9 = 00`/`+0xE7 = 01` would force base (0,1) instead of the runtime one; `+0xDD = 03` would force k10 instead of the DRO value. So everything unneeded is `FF` in the experiment.
- Out-of-range values are safe: "do not override" (`bhs` check). All contrast indices 0...6 and style indices 0...13 point to real curves; slot 27 = k20, verified by pointers.
- DRO probably works through the k7 family (`bd3`) [hypothesis from notes/tone-curve.md]. With DRO on the result would be `k0[k7fam[...]]`. Turn DRO off for the experiment.

### 7.3 Experiment "T2-k0": film k0 on all styles via Backup
- **Write:** `bk w 0003007a <block>`, single bank. Differs from stock in 6 bytes:

  | offset | was | becomes | why |
  |---|---|---|---|
  | `+0xD7` | 00 | **02** | mode 2 |
  | `+0xD9` | 00 | FF | leave base |
  | `+0xDB` | 03 | **00** | contrast = k0 (the film curve occupying contrast slot k0) + contrast enable |
  | `+0xDD` | 03 | FF | leave k7 family |
  | `+0xE5` | 00 | FF | leave style (it is disabled anyway since contrast has priority) |
  | `+0xE7` | 01 | FF | leave base column |

  `+0xDF = 07` stays: out of range < 6, so not overridden. Rollback: the stock block.
- **Expectation [code -> picture hypothesis]:** any style at any contrast slider renders with k0 tone. Standard c0 ~ the k0 test frame DSC09510 (Standard c-3): black ~12/255, soft shoulder. Vivid (Portra slot) loses the k14 S-curve and gets the same k0 tone.
- **When it takes effect.** The Backup callback updates RAM immediately, but the override is applied when tone parameters are recomputed. For the monitor probably a mode or style change is needed; for a frame, the frame itself [hypothesis]. If live view does not change, toggle the style.
- **Frames** (Daylight WB, M, one exposure, DRO off, test chart with grey scale):
  1. Before: Standard c0, Vivid (Portra) c0, Standard c-3 (k0 control).
  2. After: Standard c0, Vivid c0, Standard c+3 (globality check: the slider should stop having an effect).
- **Success criteria:**
  - Standard c0 wedge after the write matches Standard c-3 before (|dY'| <= 3 per step, black ~12/255 as DSC09510);
  - Standard c+3 after ~ the same;
  - Vivid c0 after matches Standard c-3 in tone, not Vivid before (lower contrast on steps 5-15 than k14);
  - Portra colour unchanged (matrices untouched).
- **Failure and meaning:**
  - wedge unchanged -> override not applied (mode not recomputed; retry after a style change) or the mode byte is taken elsewhere;
  - dark or linear frame -> the Backup fallback LUT kicked in (builder error). Roll back immediately.
- **Rollback:** write the stock block back, then `bk r 0003007a` = stock. Restoring `+0xD7 = 00` is enough, but write the whole block.

### 7.4 Mode 1 (assessment only)
- Format: `0x3007a+0x00...+0xBF` = 96 x u16 LE, Y values 0...1023 (10-bit tone-LUT output); `+0xC0...+0xD1` = 9 x u16 segment params, copied in order `1,0,3,2,5,4,7,6,8` [code]. Stock: Y = `2,4,...,64` (step 2), `68...128` (step 4), `136...256` (8), `272...512` (16), `576...960` (64), then `1023` x9; segments `2,2,3,4,4,4,4,3,3`.
- These Y values **directly replace the result of the whole "base -> contrast -> style" chain** [code]. So they must include **base gamma**: Y_i = film(base(x_i)), x_i being the grid nodes built by `0x2d6ba8`.
- Why stock gives a dark frame: the stock numbers equal the grid nodes (Y = x). Without base gamma this is linear output, and 18% mid grey lands around 46/255 instead of ~115 [hypothesis].
- To make mode 1 useful: (a) recover nodes x_i exactly from `0x2d6ba8` (tables `0xc39d8aca`/`0xc39d8ab8`/`0xc39d8adc`); (b) take the runtime base gamma for stills (the `0xc3cb6788` row selected by the style); (c) compute Y = k0(base(x_i)). Resolved in section 8.

## 8. Tone mode 1 (`0x3007a+0xD7 = 01`): base found, values computed

### 8.1 Base gamma and nodes [code + measurement]
- **Base table** `0xc3cb6788` (file `0x634668`): 28 rows x 2 pointer columns, 24 non-empty curves. Each curve is **2048 x u16** (11-bit input 0...2047, 10-bit output 0...1023), followed by a 13 x u16 tail. The first 9 tail values are segment params (`2,2,3,4,4,4,4,3,3`, same as `0x3007a+0xC0`), then row number and column flag [code]. **Correction to notes/tone-curve.md:** base is 2048 -> 1024, not 1024 -> 1024.
- **Which base stills use.** All 24 curves were fitted to the RAW -> JPEG pair of DSC09419 (Standard c0, DRO off, ISO 800): RAW G channel `(v-512)/(16383-512)` on 21 grey-scale steps vs JPEG G channel, only the input scale free.
  - **Best: row 0, column 1** (`0xc39d8dfa`, file `0x597dfa`): error **0.92 Y'** (of 255).
  - Fitted input scale **2043 ~ 2047**: the full RAW range maps exactly onto 11 bits, no extra gain. A second independent indicator.
  - Next candidates: (7,1) 1.24 and (6,1) 1.31, but with unexplained scales 1738 and 2574.
  - Confirmed on one RAW frame (no RAW for 09509/09510).
- **Composition check.** DSC09510 (Standard c-3, film k0) vs `k0(base(0,1))`: error 1.82 vs 6.76 for base alone (steps up to ~185/255). DSC09509 (c0, same exposure) vs base alone: 2.90. So frame = `contrast[base(x)]`, as in the code.
- **Side observation.** Above ~190/255 both 09509 and 09510 are brighter than predicted by 6-18 Y', even though the installed curve is byte-identical to the fitted film k0. So **a stage after the tone LUT lifts highlights** [hypothesis; does not affect mode 1 since it is post-LUT]. See notes/open-questions.md section 2.
- **X nodes** [code + arithmetic]. `0x2d6ba8` builds 96 nodes:
  - formula: `x = (2*(k+1)*(seg_len >> p) + seg_start)*g/256 - 1`, with lengths `8,8,16,32,64,128,256,512,1024` (`0xc39d8aca`), starts `0,16,32,64,128,256,512,1024,2048` (`0xc39d8ab8`), p = base segment params;
  - at g = 256 this gives exactly table `0xc39d8adc`: `3,7,...,127` (step 4), `135...255` (8), `271...511` (16), `543...1023` (32), `1151...2047` (128), then `2047` x8;
  - g is a coefficient from `obj+0xbe4`; byte `0x3007a+0xE0/E1` forces it to 1.0 in one branch. Measurement (scale 2043) says g ~ 1 for stills.
- **Stock `0x3007a` = (X+1)/2 exactly** (checked element-wise). So stock mode 1 is **linear output without gamma**. Prediction for DSC09419 grey scale: `0 0 1 1 2 4 6 8 11 15 19 23 27 31 35 38 42 45 47 50 50` instead of `2 2 5 10 19 31 45 61 79 98 116 129...`: the "dark frame".

### 8.2 Film value set for mode 1 (Backup data, NOT verified on camera)
- Formula: `Y_k = k0_film( base(0,1)[X_k] )`, k = 0...95, X_k from `0xc39d8adc`, k0 = the fitted film curve (see notes/tone-curve.md). These are exactly the numbers the builder puts into the LUT for Standard c-3. Prediction: **a mode-1 frame on any style and contrast ~ DSC09510** (Standard c-3) in tone.
- Block contents: `+0x00...+0xBF` = 96 x u16 LE from `64, 72, 83, 93 ... 906, 909` to `909` x8; `+0xD7: 00 -> 01`; segment params `+0xC0` untouched. 162 bytes differ from stock, all monotonic. Rollback = stock block (same as for mode 2).
- **Grey-scale prediction** at the 09509/09510 exposure (1/80, f/4.5, ISO 800), G channel:
  - ~ measured DSC09510: `12 15 20 30 42 59 77 102 124 145 163 176 187 199 209 217 223 226 230 232 233`;
  - computed without the post-stage: `16 16 19 26 39 57 77 102 125 145 164 177 187 194 200...213`, matching 09510 up to ~187;
  - error of 96 points with linear interpolation vs the full curve <= 1.2 Y'.
- **Success criterion.** Standard c0 in mode 1 ~ Standard c-3 (DSC09510 or a fresh control in the same session): |dY'| <= 3 per step, black ~12/255. Vivid/Portra c0 same tone, own colour.
- **Failure:** dark linear frame -> wrong grid or values not applied. Overexposure or midtone shift -> stills use a different base, or g != 1.
- Rollback: write the stock block, `bk r`.
- **Limitations** [code]:
  - mode 1 freezes **one** base (0,1) for everything: ISO, DRO and other base rows (rows 0...8 differ, probably by DRO or ISO [hypothesis]) stop having an effect;
  - the contrast slider and style S-curves stop working too;
  - also affects the monitor (`0x2d676e`).
- **Versus mode 2 (7.3).** Same result for Standard, but mode 2 does not freeze the base and is lower risk. Mode 1 is only needed for a **custom** curve rather than the installed k0: then recomputing 96 numbers is enough.
