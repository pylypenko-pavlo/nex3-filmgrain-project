# R — Independent critical review (Fable, 2026-10-09)

Read-only review of the atlas (`00`–`07`, `_extract/A–E,L`) plus spot checks against
`~/nex3n-dump/`. Goal of ranking: **film grain + film look in the SOOC JPEG, camera kept
recoverable.** Nothing was written to or run on the camera. F/G/H extracts (Q-5/Q-2/Q-31)
were not present at review time.

Self-checks I ran on the data (not from the notes):
- `kemco.txt` is in `nflasha2_unpacked/` (p2), not p3 — confirms Q-9 / C-PART-005 error (see F-1).
- `strings` of the 33 kmods, `vmlinux.bin`, `boot1`, `bootrom`, all p8 `.so`: **zero** hits for
  `sabin` / `idt_cam` / `/usr/share/dspbin` / a codectype→path string → the module-path resolver
  (Q-2) is genuinely not in any image on disk (supports C-MOD-010 as a true unknown, not a miss).
- `boot1`: the only updater strings are `\updater\mode`, `LDR: Check boot_is_updater`,
  `LDR: <UPDATER>`; they have **no 4-aligned literal-pool reference** in boot1 — the file-flag
  reader is reached another way, so the "format of `\updater\mode` is wrong" escape (R-11) is live.
- `sen.elf` (16,856 B) links `libsencore.so`; `libsencore.so` exports `FileControl`,
  `MemoryDump`, `AdjustControl`, a full `Usb` class with `onCompleteAuthentication`, and reads
  `/dev/mem`, `/dev/nflasha5`, `/setting/sen/smode` — so senser's USB service channel lives in
  `sen.elf`+`libsencore.so`, started from `/setting/sen/smode`, independent of appFw (bears on Q-5).
- `build_multibuf.py` grains only `OFFS=[0x5e4,0x1f24,0x24e8,0x3858]` session fields — confirms
  **no build ever grained the located develop canvas** `0x8a000000`-class (see finding #1).

---

## Top 10 (first screen)

1. **"ARM path CLOSED" is overstated.** C-PIPE-001 is proven only for `session[+0x5e4]`, the
   rec40 input, and `session[+0x3e24]` (a handle). The one buffer that E-0031 proved *is* the
   developed canvas the encoder consumes — `DMM_HANDLE_YCC_FULL`, located live at `0x8a000000`,
   stride `0x2660` — was **never grained**. The decision tree in `07 §1` collapses "ARM" to those
   three transient buffers and marks it closed. The real statement is "grain written *before/into
   develop* is overwritten by the 31 develop-core passes." Graining the canvas *after* the last
   develop pass is untried. **This is the single biggest hole.** (see 1-A, 3-A)

2. **The canvas base is reachable without solving the handle resolver.** `0x83dcc9xx`/`0x83dce2xx`
   descriptor tables hold the per-frame YC_FULL base 37× at stride `0x3c`, offset `+0`
   (safe-test-boot §4a; C-MEM-012 only shows the *accessor* `0xc36045fc` fails). A p3 hook late in
   capture can read the base from that table and grain the canvas. Q-20 frames this as "unresolved
   handle→DRAM"; it is partly resolved already and not in the decision tree. (see 3-A)

3. **E-0049 — the keystone of #1's "closed" verdict — is self-admittedly mislabelled.** R-6:
   DSC09548 was shot at 09:04Z, before the marker image was flashed at 11:11. The "0 % black
   everywhere incl. Off frames" proof that `session[+0x5e4]` is not the encoder buffer rests on an
   off-by-one frame set. The conclusion is probably right, but it is *assumed*, not shown. (2-A)

4. **MSDump (C-MOD-032) is under-ranked.** `YKNR_Debug_MSDump`, `MSDumpYCTarRef`,
   `/mnt/YC_FILE%04x.dat`, gate `camdebug_get_file_switch_info` — a built-in dump of the actual YC
   buffers to the card. This is the one cheap experiment that could *directly* identify the
   encode-input buffer and settle #1/#3 with observation instead of inference. Q-10 rates it
   "medium." It should be near the top. (5-A)

5. **Chroma-by-luminance is wrongly treated as "not available."** C-COL-021 (hue records have no L
   dependence) is used in `02 §3` hole 4 and the shoulder discussion as if no lever exists — but
   C-COL-026 (`Create3DLUT`, Y axis 5 nodes, editable reference LUT `[obj+0xa0]`) **is** a native
   chroma-by-luma lever and the atlas even says so in Q-7. Two pages draw opposite conclusions from
   the same fact. The film-shadow/highlight desaturation that defines a film look is likely already
   reachable through the 3D-LUT reference, not blocked. (4-A, 1-B)

6. **The Linux route (Q-1) is ranked "cheapest/safest first" but its recovery channel is
   unverified.** The "harmless dry run" of Q-1 *is* the dmode=`"03"`+env.txt write that could select
   a kernel-only or broken-userland boot; recovery then needs the same USB updater that C-SAFE-013
   says may be unreachable in that state. "No firmware partition written" ≠ low risk. p3 has a
   *proven* recovery (28/0); p2 boot-chain edits do not. The ranking inverts the actual risk order.
   (6-A)

7. **`sa_yknr` as the grain host rests on a chain of hypotheses, every link unproven.** Q-31's "NR
   module = grain host" needs: yknr runs on stills (C-NR-007 hyp) **and** writes luma (C-MOD-026,
   luma/chroma "not established", notes disagree) **and** the file-id resolver honours `/setting/`
   (C-MOD-010 unknown) **and** VLIW op3 semantics known (C-DSP-015 unknown). Four unknowns multiplied.
   The DSP branch of `07 §1` should show this as a conjunction, not a path. (1-C)

8. **The idt_cam NOP bisection (E-0052–E-0062) cannot support *any* positive stage claim, yet
   C-IDT-009 is kept `hypothesis` over extract B's `refuted`.** R-1 is correct: NOP bundles run as
   scalar code are random branches. Keeping Campaign-A labels at `hypothesis` (even flagged) lets
   them leak back into reasoning (they still populate the overlay-table "Campaign A label" column and
   the `02` pipeline prose). They should be `refuted` with the *observations* kept separately. (4-B)

9. **"No native grain generator" (C-PIPE-004) is a disputed-scope negative promoted toward fact.**
   The PRNG/LCG sweep scope is explicitly disputed (FPP "all sa_*" vs DG "p3 only", Q-26 open), and
   HC-Mono's grain being "amplified sensor noise" is inference from one EXIF mismatch. Using this to
   deprioritise reusing an existing texture is premature. (3-B)

10. **Delivery/safety assumes WBI-zero is load-bearing with zero control runs (C-DLV-009).** Every
    one of 28 flashes zeroed WBI; no flash ever omitted it. The entire "cold boot re-reads the file"
    model (C-BOOT-018) and the recovery argument depend on an untested step. Cheap to test (Q-19),
    high consequence if wrong. (6-B)

---

## 1. Logical holes / inflated status on the path to grain

**1-A (C-PIPE-001, status verified-hw → the *scope* is inflated).** Verified: graining
`session[+0x5e4]`, rec40 input, `session[+0x3e24]` does not reach the JPEG. Not verified: that *no*
ARM-writable buffer reaches it. E-0031 located the developed canvas `DMM_HANDLE_YCC_FULL` at
`0x8a000000` (the thing the encoder reads by handle, C-MEM-005/C-CTRL-007). `build_multibuf.py`
(checked: `OFFS=[0x5e4,0x1f24,0x24e8,0x3858]`) and every flashed build grained session sub-buffers
or a handle id — never the canvas at its resolved base. *How to settle:* finding 3-A experiment; or
MSDump (5-A). Until then the decision-tree node "ARM path … CLOSED" should read "ARM writes into
pre-develop/transient buffers are overwritten; the post-develop canvas is untried."

**1-B (C-COL-021 / `02 §3` hole 4).** "No mechanism for chroma-by-luminance is known" contradicts
C-COL-026 on the same page. The HW 3D LUT has a 5-node Y axis and is filled from an editable
reference LUT scaled by Level. That is exactly a shadow/highlight desaturation lever. The atlas
should not list this as a blocking hole; it is Q-7, cost M, and probably the cleanest film-look win
that does not touch grain at all.

**1-C (Q-31 / DSP branch).** The "`sa_yknr` = grain host" path is drawn as a sequence in `07 §1` but
is a conjunction of four independent unknowns (yknr-on-stills, luma-write, resolver honours
`/setting/`, VLIW op3 authorable). My resolver check (zero `sabin` strings anywhere) makes the third
link worse than "unknown" — there is no evidence the resolver is even reachable to influence. Rank
the DSP grain path *below* the canvas route and the Linux route, not between them.

**1-D (C-TONE-024, "highlights held above Y′≈200", verified-hw on ONE frame).** The whole "film
shoulder is blocked" sub-thread rests on a single wedge pair (DSC09509/09510) with differing
exposure (its own caveat). Status verified-hw is defensible for "it happened once" but the *model*
(`out≈max(LUT, base−δ)`) is one frame. Q-6's +1/+2 EV test is right; until then do not treat the
shoulder as a hard constraint when designing curves.

**1-E (C-MEM-017 / C-DLV-010, the one "it works" result).** The live av-cam differs from stock only
in the k0 curve region — good — but R-13 notes **no flash log survives** for that write. The content
is inferred from a later live read. It is the single proof that a narrow p3 write is safe+effective;
it should carry the R-13 caveat wherever it is cited as the safety precedent (it is cited as
precedent in `05` channel 5 without the caveat).

## 2. Alternative explanations for logged observations (esp. E-0045–E-0066)

**2-A (E-0049).** Already flagged R-6. Alternative reading that is *not* excluded: the marker *did*
write the right buffer on the one correctly-ordered frame, and the "0 % black" came from the
mislabelled earlier frame. The claim "`session[+0x5e4]` at rec40 is not the encoder buffer" is
probably true but the experiment as recorded does not exclude the opposite. A re-shoot (same build,
careful frame bookkeeping) is the fix and is nearly free.

**2-B (E-0045–E-0048, amplitude independence).** The atlas reads flat HP-std across ±14/±31 as "the
buffer is discarded." Equally consistent: the grain *is* written to a live buffer but a **later
full-frame NR/averaging pass** (YKNR/PBE/CCNR_Enc, all post-develop per the stage names) smooths
white noise back to ~1 regardless of input amplitude — which would also explain why native HC-Mono
"grain" survives (coarse, correlated, ACF lag-1 0.58) while fine white noise does not. If so, grain
must be **spatially correlated / added after NR**, not rejected outright. This reframes the goal from
"find the encode buffer" to "add correlated grain after the last NR stage," and it is testable: grain
with a 2×2 or 3×3 correlated kernel at the same site and see if it survives where white noise did not.
Not considered anywhere in E-0045–E-0048.

**2-C (E-0057/E-0058 black/white vs E-0060).** R-2 already offers the statistics-overlay explanation.
One more not listed: these ranges include the `0x105d0` AE/stat overlay *and* its DMA literal pool;
corrupting the DMA descriptor (`0x48234`/`0x48230`) would stall the *engine*, and "black luma, dies
after shot" / "white, dies" are exactly engine-hang-mid-frame symptoms, not tone-stage removal. The
severity difference E-0058 vs E-0060 (both cover `0x105d0`'s program) then comes from how far the
NOP run extends into live DMA setup, not from any luma stage. Supports treating all E-005x/E-006x
*positive* results as engine/stat damage, i.e. strengthens the case to mark C-IDT-009 refuted.

**2-D (E-0038, always-run hook, no grain).** Read as "gate false / wrong buffer." Alternative: the
hook *ran and grained* `session[0x3e24]`=`0x1df` (a handle, E-0040) → it wrote 8 MB at bus `0x1df`
= DRAM `0x800001df`, i.e. into low kernel/av-cam RAM, not a frame — which is *also* why the camera
still booted and shot (the region is not fatal) and why no grain appeared. Same end state, but it
means E-0038 tells us nothing about the gate (R-7) — consistent with downgrading C-CTRL-009 to
unknown, which the atlas already did. Fine; just don't cite E-0038 as evidence about the gate.

## 3. Missed paths to the goal (absent from `07 §1`)

**3-A — Grain the developed canvas, base read from the descriptor table (ARM/p3).** *Highest-value
missed path.* Hook a stage that runs **after the last `0xc37ea42e` develop pass and before
`DistEncodeFULL`** (e.g. a `Stage_SortJPEG` / `DistEncode_Base` entry, C-PIPE-005/018), read the
YC_FULL base from the `0x83dcc9xx` descriptor table (+0, stride 0x3c; present 37×), add correlated
grain to the Y plane of the full canvas, return. This sidesteps the handle resolver (C-MEM-012) and
the "transient buffer" failures. Feasibility: medium — needs the right late site and confidence that
the table entry is still valid at that point, both checkable offline. This is strictly more promising
than any idt_cam/DSP route and is simply not in the tree.

**3-B — Reuse an existing texture instead of generating grain.** The atlas treats grain as something
to *inject*. Two existing textures are already full-frame and survive to JPEG: (a) **native high-ISO
noise** — shoot the grain source at high ISO and *suppress NR less* (NR-1…NR-4, C-NR-010..013, all
designed, none run) so the sensor's own luma noise becomes the grain; (b) the **Soft Focus / Toy
convolution engines** already do authored full-frame spatial filtering via DSP and are the *one*
pixel path proven to reach the file (SF blur is visible in JPEGs). A Soft-Focus kernel that is a
high-pass "add noise texture" rather than low-pass is a long shot (kernels must sum to 256,
C-MOD-021) but the *vignette/Toy* and *NR-off* routes are cheap, Backup-only, and reach the file.
Only NR-1…4 appear in the tree (as "native-noise substitute, cheapest"); the framing should be
promoted from footnote to a first-class branch because it is the lowest-risk route that is *known* to
affect the JPEG.

**3-C — MSDump as a delivery-adjacent observation path.** Not a grain path, but it unblocks every
other one by naming the encode buffer (see 5-A). Belongs in the tree as the precondition node.

**3-D — a7-IV-style: character in a post-LUT.** The 3D-LUT reference (C-COL-026) plus the base-gamma
row/col (C-TONE-013) are the camera's own "look" surface. A film look (tone + chroma-by-luma +
split-tone) can be fully authored there *without grain*, delivering most of the "SOOC film"
subjective goal while the grain question stays open. The atlas separates colour and tone work from
"the goal" (grain); for the *stated* goal ("film look straight out of camera, like X100") colour+tone
via 3D-LUT is 80 % of the result and is nearly done. Worth an explicit "ship the look now, grain
later" branch.

**3-E — Video path.** Not examined anywhere. AVC encode uses `sa_avce_*` and there is an **unused
H.264 SEI film-grain validator** already noted in C-PIPE-004's sweep. Movie frames extracted as
stills, or the SEI grain path, are an untouched alternative substrate. Low priority for the stills
goal but genuinely absent.

## 4. Contradictions between pages left unflagged

**4-A.** `02 §3` hole 4 ("no chroma-by-luminance is known") vs C-COL-026 + Q-7 (the 3D-LUT *is* one).
Same page, opposite claims. (see 1-B)

**4-B.** `04` keeps Campaign-A labels `hypothesis` (C-IDT-009, editor override) while `06` R-1 and
`04` itself (C-IDT-007 refuted) say the NOP method cannot support them. The overlay table (`04 §5.1`)
still carries a "Campaign A label" column and `02`'s pipeline text inherits the "idt_cam = 3A" lean
as if partly earned by the bisection. Decide once: observations verified-hw, interpretations refuted.
Q-3 of `04 §7` explicitly asks for this reconciliation and it is still open.

**4-C.** `C-PART-005` lists `kemco.txt` in p3; I confirmed it is in **p2** (`nflasha2_unpacked/`,
3220 B, with `cmpr.path=/system/sabin/ssboot.bin`). `C-BOOT-025`/`C-MOD-018` say p2. `01`'s partition
table row for p3 still implies kemco via "config"; fix C-PART-005. (Q-9/Q-I, open.)

**4-D.** `C-BK-002` (write applies immediately to the RAM copy) vs `C-BK-003` (reboot needed). `03 §2.1`
resolves it operationally ("reboot anyway") but Q-23 is still listed open and `07`'s conflict table
keeps both — the operational resolution and the "open conflict" coexist without cross-reference.

**4-E.** `C-JPEG-004` (HW coder, tables in av-cam) vs SB §7(a) quoted inside it ("DSP encodes,
sa_jpeg_enc/zima"). The claim contains its own contradiction; Q-4/Q-5 open. Fine to keep, but
C-MOD-029's "unknown" and C-JPEG-004's "hypothesis (HW)" assign different statuses to the same fact.

**4-F.** C-MEM-005 (canvas 4912 wide, stride 0x2660) vs C-MEM-009 (per-stage copies 4928 wide). Page
01 flags this as "two geometries, do not mix," but `02` stage 15 lists both in one cell without the
warning, and a grain build that assumes the wrong stride (e.g. 9856 in E-0044's stripe) silently
mis-strides. Any canvas-grain build (3-A) must use 0x2660/4912, not 4928 — call this out in `05`.

## 5. Cheapest experiments, maximum information (predictions per hypothesis)

**5-A — Enable MSDump, dump the encode-input YC to card.** Disassemble
`camdebug_get_file_switch_info`, flip its Backup gate (likely `0x00030056` bit, C-BK-008 — one byte,
revertable), shoot one frame. *Cost S–M, risk low (shared debug block, revert one byte).*
- If the JPEG-matching YC file is dumped at the geometry of the `0x8a000000` canvas → confirms the
  canvas is the encode input → **greenlights 3-A**, and tells you the exact stage index.
- If it dumps a buffer at a *different* base than any session field tried → identifies the real target
  directly.
- If the gate is not in Backup / nothing dumps → MSDump is code-gated; fall back to 3-A blind. Either
  way you learn where the pixels the encoder reads actually live — the one fact that blocks the ARM
  branch.

**5-B — Correlated-grain canvas hook (one p3 flash).** Build the 3-A hook: late post-develop site,
base from `0x83dcc9xx[+0]`, add **spatially correlated** grain (2×2 block or value-dependent) to Y.
*Cost M (proven p3 flash + recovery), risk low (C-SAFE-003, 28/0).*
- If visible film-like grain appears in the SOOC JPEG → **goal reached** via ARM, DSP/Linux unneeded.
- If grain appears but is smoothed to ~1 HP-std like before → confirms 2-B (a late NR pass eats it)
  → next step is to move the hook after the last NR stage or raise correlation length.
- If nothing appears → the canvas is *also* re-read by handle past this point → only then is the ARM
  branch genuinely closed, and Linux (Q-1) becomes the route.

**5-C — NR-off film-grain-by-sensor (Backup only).** Write NR-1 then NR-3 (C-NR-010/011), shoot at
ISO 1600/3200, measure σL*/σC*. *Cost S, risk low (Backup, both banks, rollback bytes).*
- If σL* rises with σC* held → you have a real, correlated, SOOC luma grain *today*, no firmware
  write, that is *known* to reach the JPEG. Possibly the whole goal, cheaply.
- If σC* rises too / blotches → stop, revert; tells you GHNR/GLNR is doing chroma denoise you want.
- Either way it calibrates how much "grain" the native pipeline can yield before any hook.

**5-D — 3D-LUT reference edit, one node (chroma-by-luma).** Locate the reference LUT source
(`[obj+0xa0]`, Q-7) in av-cam data, change one Y-shadow node's chroma down, one p3 narrow write.
*Cost M, risk low (narrow p3 write precedent C-DLV-010).*
- If shadow chroma drops without touching greys → film shadow desaturation confirmed authable →
  closes the "no chroma-by-luma" hole (1-B) and delivers a core film trait.
- If no change → the reference LUT is elsewhere / Create3DLUT not on the stills path → re-open Q-7.

**5-E — Re-shoot E-0049 with clean frame bookkeeping.** Same `p3_markrec40` build, one Off frame and
one SF frame, record DSC numbers at the camera. *Cost S (one flash already characterised).*
- If both frames are 0 % black → C-PIPE-001's scope is correctly "rec40 input not encoder buffer"
  (retires R-6).
- If the correctly-ordered frame is *not* black → `session[+0x5e4]` partially reaches the file and the
  "closed" verdict is wrong. Cheap insurance on a load-bearing claim.

Ranking for the goal: **5-A and 5-C first** (one observes the target, one may deliver grain with zero
firmware risk), then **5-B**, then 5-D (look, not grain), 5-E (hygiene).

## 6. Safety risks the atlas underrates

**6-A — Linux route recovery is unproven, yet Q-1 is ranked cheapest/first.** `05` channel 10 says
"DO NOT WRITE until C-SAFE-013 answered," but `07`'s decision tree and ranked table put Q-1 (dmode
`"03"` + env.txt) at the top with cost S, calling it the route that "needs no firmware partition
write." The Q-1 "dry run" **is** the risky write. If `init`/a preload crashes before `sen.elf`'s USB
service comes up, the only recovery is a p2 edit that needs the very USB that may be down. My check:
`sen.elf` is forked from init and the senser USB channel is in `sen.elf`+`libsencore.so` reading
`/setting/sen/smode` — whether it starts *before* the appFw stage and *survives* a crashing
`LD_PRELOAD` is exactly C-SAFE-013 and is unknown. **Do not rank Q-1 above p3 work until Q-5 is
answered statically** (the atlas says this in prose but the table ordering contradicts it). p3 has
28/0 recovery; p2 boot-chain does not have 1.

**6-B — WBI-zero is load-bearing and never controlled (C-DLV-009, hypothesis).** The recovery model
("cold boot re-reads the file") and every flash depend on zeroing p5 sector 0. No run ever skipped it.
If the assumption is wrong in some state (e.g. a warm restore that skips `init` entirely, which
LR §3 itself raises for the env.txt route), a bad image could be restored from WBI in a loop. Q-19 is
cheap; treat WBI-zero as unverified, not as a known-good step.

**6-C — "p3 is safe (28/0)" conflates av-cam with kernel/initrd.** C-SAFE-003 is proven for *av-cam
and idt_cam* corruption. Every whole-partition `flash_any.py` write *also* rewrites `vmlinux.bin` +
`initrd.img` in p3 (C-DLV-011), and an interrupted write or a bad patch in that region has **never**
been exercised (C-SAFE-014). The "0 bricks" figure should not be read as "p3 writes are safe" but as
"av-cam/idt_cam *content* changes recovered." Any experiment that edits the p3 kernel/initrd (none
planned, but 3-A tooling writes the whole partition) carries unquantified risk. Prefer the **narrow**
p3 write (channel 5, sectors inside av-cam only) for 3-A/5-B if the hook fits one LZPT block, exactly
as the k0 curve did — this keeps the kernel/initrd bytes untouched.

**6-D — Backup "protected" writes rewrite the whole file (E-0002).** Any `bk patch` on an
attribute-01 block rewrites all 703,962 B of Backup and mutates mode flags + checksum. The atlas
notes it but rates channel 1 "ALLOWED." A failed/interrupted `bk patch` is a whole-Backup risk, not a
one-block risk; the colour/tone work uses only unprotected `0x0003*` blocks, so keep it that way and
never let a plan quietly promote to `bk patch`.

**6-E — `0x0003007a` mode-2 base-gamma fallback (C-SAFE-002).** The rule "in mode 2 `+0xD9`/`+0xE7`
must stay FF or the capture path falls back to a Backup LUT (probably a dark linear frame)" is a
*designed* prohibition never tested — a mistake here does not brick but could produce a black/garbage
live view that looks like a fault. Low stakes, but the tone-mode experiments (Q-12) should be shot
with a known-good `bk` rollback staged first, since mode 1 also changes live view (C-TONE-018) and a
bad frame could read as "camera broken."

---

### One-line verdict
The colour/tone look is nearly shippable (3-D/5-D) and under-credited toward the stated goal; the
grain conclusion "ARM closed" is the weakest load-bearing claim in the atlas because the one buffer
that is the encoder's input was located but never grained (1-A/3-A), the proof frame set is
mislabelled (2-A), and a late-NR-smoothing alternative was never tested (2-B). Cheapest high-info
moves: enable MSDump to see the encode buffer (5-A) and try NR-off sensor grain (5-C) before any more
idt_cam/DSP effort. Safety: the Linux route is mis-ranked as safest (6-A) and WBI-zero is unproven
(6-B).
