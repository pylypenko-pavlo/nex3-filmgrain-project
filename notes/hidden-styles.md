# Hidden Creative Styles: who hides them (static analysis)

Read-only code comparison. No camera writes, no patches, no modified files.
Continues the "hidden Creative Styles" finding in the README and `notes/backup-params.md`.

## 0. Summary

1. **The original premise was wrong: the NEX-6 also shows only 6 styles.** Per its spec, NEX-6
   Creative Style = Standard, Vivid, Portrait, Landscape, Sunset, B/W; no Watercolor or
   Illustration in Picture Effect, no Style Box
   ([mhohner.de NEX-6 tech data](https://www.mhohner.de/sony-minolta/onebody/nex-6?lg=e);
   [Adorama](https://www.adorama.com/isonex6bc.html)). The 13 styles and Style Box arrived later
   (a6000 / A7). A 3N-vs-NEX-6 diff therefore could not find a difference.
2. **The filter is code, not a setting.** In `lib/viewUnified2.so`, during initialisation of the
   `view/CAMERA_CREATIVE_STYLE` view, an **unconditional** loop marks menu items with IDs 6..12
   (Neutral, Clear, Deep, Light, Night Scene, Autumn leaves, Sepia) as invalid (`valid = 0`). It
   checks nothing (model, settings store, inhibit table, av-cam reply): it simply walks the
   constant table `{6,7,8,9,10,11,12}`. **[verified by disassembly]**
3. NEX-6 v1.03 has the same loop, the same table and the same 13-item list; the function is
   instruction-identical apart from addresses.
4. **"Which runtime parameter decides?" is moot: none does.** That is why the 18 `0x0107xxxx`
   flags had no effect on the camera; nothing on this path reads them.
5. **Style Box, Watercolor and Illustration are not in any menu**, on 3N or NEX-6. UI strings
   exist ("Style Box", "Watercolor", "Illustration: Low/Mid/High"), libObj has the parameters
   (`PARAMID_WATERCOLOR_EFFECT_LEVEL`, `PARAMID_ILLUST_EFFECT_LEVEL`, `COLOR_MODE_MEMORY_NUM`),
   but **no menu-item structure in any `lib/*.so` references their string IDs**. Not hidden:
   simply never wired in. **[verified by search]**

## 1. Where it is decided (3N, `viewUnified2.so`, SHA-1 `cd32d15f...`)

Creative Style view: class `ViewCameraCreativeStyle` (RTTI `23ViewCameraCreativeStyle`, vtable
@ `0x67c88`/`0x67d98`), created via `ViewCameraCreativeStyleToInstance` @ `0x16983` ->
constructor `0x45000`. Style list and parameter column: `CmnViewMenuData` +
`MenuSetSeperateCreativeStyle`.

Menu init at `0x44374` (vaddr, Thumb):

```
44394  blx CmnViewMenuData::initMenuData(items=0x656d4, inconst=0x656fc, 0, SetSeperateIF)
4439a  loop r5 = 0..6:
         r1 = [[GOT 0x6191c] + r5*4]        ; table @ 0x65768 = {6,7,8,9,0xa,0xb,0xc}
         bl 0x442f0(this, r1)
443ae  cmp r5,#7 / blt
...
443e8  loop r5 = 0..12: bl 0x43fd4 -> contrast/saturation/sharpness for each of the 13 styles
```

`0x442f0` (helper, no conditions):

```
menu->vfunc[+0x74](id, &item)     ; libObj 0x5af99c: find item by ID
menu->vfunc[+0xa0](item, 0)       ; libObj 0x5afc70: inconst[idx*3+2] = 0 -> item invalid
```

The meaning of `+0xa0` was confirmed via the exported
`CmnViewMenuData::setItemValid(item*, int, bool)` @ libObj `0x5ab5db`, which calls the same
virtual. The `CmnViewMenuData` vtable was located from RTTI `15CmnViewMenuData` (typeinfo
`0x10057d4`).

Menu data (`CmnViewMenuItemStruct` {items*, count=13, 13, ...}; item = 0x28 bytes, ID at +8,
string ID at +0xc):

| ID | string | style |
|---|---|---|
| 0 | 0x126 | Standard |
| 1 | 0x146 | Vivid |
| 2 | 0x147 | Portrait |
| 3 | 0x148 | Landscape |
| 4 | 0x149 | Sunset |
| 5 | 0x14a | Black & White |
| 6 | 0x063 | Neutral (hidden) |
| 7 | 0x064 | Clear (hidden) |
| 8 | 0x065 | Deep (hidden) |
| 9 | 0x066 | Light (hidden) |
| 10 | 0x06d | Night Scene (hidden) |
| 11 | 0x06e | Autumn leaves (hidden) |
| 12 | 0x070 | Sepia (hidden) |

Initial inconst state (`0x656fc`): every one of the 13 items has the triple `00 02 01`, i.e. the
last byte valid = 1. The items are declared usable; only the loop disables them.

The other checks in this view control **greying out**, not hiding:
`getModelInfo("model/INH_WRAPPER", ..., param 0x101 = feature)` @ `0x43388` (inhibit queries
0xfa..0x108 -> `DefInh::sm_refTbl`), `Bkup_Read(0x01070316)` @ `0x4345c` and `Bkup_Read` @
`0x449de`. In `sm_refTbl` visible and hidden styles look the same: rows 0xfc..0x105 are
bit-identical, and B/W and Sepia (0x106/0x108) differ by the same set of 25 factors. Nothing is
filtered by model.

## 2. Comparison with NEX-6 v1.03 (`viewUnified2.so`, SHA-1 `3d6d560a...`)

- Init at `0x3158c`: same `initMenuData`, same 7-iteration loop -> `0x31568` (same
  `vfunc+0x74` / `vfunc+0xa0(item,0)`), table @ `0x5fa98` = `{6,7,8,9,0xa,0xb,0xc}`.
- Item list @ `0x5f7fc`: same 13 items, same IDs and strings; inconst @ `0x5fa2c` also
  `00 02 01` x 13.
- Functions paired via vtables (`code/hidstyles/fpair.py`): the init body is
  instruction-identical. Other differences come from reordered functions and literal pools, not
  different logic.
- `share/app/master_rec.uxc` and `viewCameraCreativeStyle.uxc` are byte-identical.

Conclusion: 3N and NEX-6 suppress the seven styles with the same code, consistent with the
NEX-6 spec (6 styles).

## 3. A second style list (`viewUnified4.so`), for reference

`viewUnified4.so` (identical on 3N and NEX-6) has another item table: IDs 0x99..0xa5 in the
order Standard, Vivid, Neutral, Clear, Deep, Light, Portrait, Landscape, Sunset, Night, Autumn,
B/W, Sepia, plus two service items (0xa6, 0xa7). It is referenced by the descriptor @ `0xa4de0`
{items=`0xa4a70`, count=0xf, ..., string 0x145}, next to Fn-menu items ("Metering Mode",
"Select the desired effect..."). **[hypothesis]** This is the Fn / Quick Navi table, where all 13
styles are not statically hidden. Whether that path is reachable on the 3N (which has no Fn
button) and how inhibits apply there is unverified. This is the first lead to follow.

## 4. Style Box, Watercolor, Illustration

- Picture Effect list in `viewUnified2.so` (items @ `0x5aef4`...): Off, Toy Camera, Pop Color,
  Posterization Color/B&W, Retro Photo, Soft High-key, Partial Color x4, HC Mono; then Soft
  Focus, HDR Painting, Rich-tone Mono and Miniature (Rich-tone and Miniature found in
  `viewUnified4` and `viewUnified2 0x5b6e4`). Watercolor (string 0x10e0) and Illustration
  (0xf66/0xf87/0x103e/0x1177) **appear in no item table**: searching all `lib/*.so` of 3N and
  NEX-6 for 32-bit string IDs `0x0200xxxx` finds nothing.
- Style Box (string 0x9c1): likewise no references; libObj only has
  `COLOR_MODE_MEMORY_NUM(_TYPE)`.
- So for these three there is no filter, inhibit or flag: they were never added to the menu (on
  3N or NEX-6). Their handling in libObj and av-cam (`PARAMID_*`, `Start_Art_Effect`) is reachable
  only by passing a value around the menu. **[hypothesis, unverified]** whether the 3N's av-cam
  would render Watercolor / Illustration given such a value; per `notes/sony-dsp-generations.md`
  no generation has a dedicated SA module for them.

## 5. Verified vs hypothesis

**Verified (statically):** the unconditional hide loop for IDs 6..12 and its table on 3N and
NEX-6; `vfunc+0xa0` = setItemValid(item, false) (via the exported libObj wrapper); ID -> string
-> style mapping; initial valid=1 for all 13 items; identical `master_rec.uxc` /
`viewCameraCreativeStyle.uxc`; no menu references to Style Box / Watercolor / Illustration;
NEX-6 spec = 6 styles (two external sources restating the official spec).

**Unverified / hypothesis:** the purpose of the `viewUnified4` table (Fn / Quick Navi) and its
reachability on 3N; what av-cam does with style values 6..12 arriving around the menu (libObj
has the App->Obj mapping 0x16d..0x17b for all 13, see libObj `0x94c51c`); anything about
Watercolor / Illustration in av-cam.

## 6. How to reproduce

Tools in `code/hidstyles/` (capstone + pyelftools). They take paths to your own unpacked
userland libraries (`lib/*.so` from the camera's rootfs); none are shipped. The NEX-6 reference
is the official v1.03 updater, unpacked with fwtool.

- `elfx.py`: ELF loading, PLT parsing (Thumb `bx pc` stub + 3 ARM instructions) -> import
  names, a disassembler that skips data.
- `ann.py <so> <from> <to>`: disassembly annotated with calls, literals and PIC strings.
- `callers.py <so> <regex>`: all call sites of an import (exhaustive BL/BLX scan).
- `vtp.py`, `fpair.py`: vtable pairing 3N <-> NEX-6 and function comparison.
- `l4.py`: dumps a menu-item table with string names; set `NEX3N_STRINGS` to the camera's
  `share/app/string_english.uxc`.

## Second 13-style list in `viewUnified4.so` (follow-up)

**Conclusion: on the NEX-3N there is no stock way to reach Neutral/Clear/Deep/Light/Night/Autumn/Sepia.**

- The list at descriptor `0xa4de0` is the sub-item table of the "Creative Style" row (8th row) in the Brightness/Color menu (rows: Exposure Comp., ISO, WB, Metering, Flash Comp., DRO/HDR, Picture Effect, Creative Style), read only by `ViewBrightColorMenu` (`view/BRIGHTCOLOR_MENU`). Its 15 entries (13 styles in a6000 order + 2 blanks) appear to serve only for displaying the current style name in the value column (hypothesis: no code opening it as a selection list was found). NEX-6 data is identical.
- Pressing Enter on the row (`0x5fb9a`) calls `openView("view/CAMERA_CREATIVE_STYLE")` (`0x5fbd0`) — the same view that unconditionally hides IDs 6..12.
- "Creative Style" is assignable to keys (AEL, Soft key B, Right key, Custom 1-6). In shooting mode the key handler `ViewStlRecClassic` (libObj `0x6fb858`, function code 0xd) also opens `view/CAMERA_CREATIVE_STYLE` (`0x6fb9f4`). The Fn-menu view `view/FNSET_CREATIVE_STYLE` has no module in either the 3N or the NEX-6 firmware.
- Greyed-out state (`isItemGreyout`/`setGreyOut`, `INH_WRAPPER` queries) is separate and does not cause the hiding.
- Selection is sent via `requestModelExecute("model/CAMERA", 0x26, ...)`; the menu-item -> style-value mapping (`0x434e4`) covers all 13: Standard 1, Vivid 2, Neutral 3, Portrait 4, Landscape 5, B&W 6, Clear 7, Deep 8, Light 9, Sunset 0xa, Night 0xb, Autumn 0xc, Sepia 0xe. No model check on the Linux side; whether av-cam applies values 3/7/8/9/0xb/0xc/0xe is untested (parameters for all 13 exist in the 3N settings store).
- Not checked: the Brightness/Color popup layout (`0x61eac`) and Quick Navi (`ViewCustomLauncher`).

## Picture-effect activation path - no no-flash bypass (2026-10-06)

Investigated whether an unwired picture effect (e.g. Rough Monochrome, for its grain) could be activated without a firmware write, by setting the effect value outside the menu.

- The active picture effect is set by an **internal message** `SetPictureEffectForLiro` (CamUser::CamMsgConv) from the app/UI to the imaging core; `libObj`'s ObjEffect maps the selected effect to `PARAMID_ARTFILTER_FILTER_ID`. The available list is built by a UI converter in `viewUnified2` (same pattern as the Creative-Style `{6..12}` filter).
- **No imaging-Backup property** for the picture effect was found (nothing `bk`-writable), **no PTP/SDI device property** for it, and persistence of the UI selection lives in the app framework (`/setting/appfw_infra`), not in the imaging Backup store.
- Therefore there is **no external, writable key** to set the picture effect past the menu filter. Activating an unwired effect requires changing the UI/app code or injecting the internal message - i.e. running or modifying userland, which means a firmware-partition write (the boundary held throughout this project).
- Consequence for grain: the firmware grain generator (Rough Monochrome) cannot be reached no-flash, and even if reached is B&W only (see `notes/film-effects-plan.md`). In-camera, no-flash grain remains limited to native sensor noise (ISO-linked). Synthetic grain at arbitrary ISO, or grain on colour, is not achievable in-camera within these constraints; the realistic route for that look is an offline grain pass on clean captures.
