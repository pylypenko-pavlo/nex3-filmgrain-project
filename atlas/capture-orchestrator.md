# Capture orchestrator — the stage router (2026-10-17)

How the still-capture pipeline decides **which processing stage runs at each step and which DSP module it opens**.
This is the "routers/orchestrators" layer (above the individual DSP modules mapped in `04-dsp-modules.md`).
Supersedes the "statically-walked step-table" reading in C-PIPE-027/028 (those were right about the *components*,
wrong about the *dispatch mechanism* — see §5).

## 0. The tooling unlock that made this possible (answers "why was the data segment missing")
`av-cam.bin` as unpacked by sonygen is only the **first 6.55 MB** (`0x6401d8`, code segment) of the full av-cam
image. The real image is **`nflasha3_unpacked` (15 MB, `0xe60000`)**; `av-cam.bin` is the slice starting at **offset
`0x8e00`** of it. Everything above VA `0xc3a811d8` (~8.5 MB: the ARM-mode region, the C++ registry/RTTI, the colour
master tables `0xc3bad724`, the RAM-copy images) sits in `nflasha3_unpacked` but was **never carved into av-cam.bin**
— which is why descriptors at `0xc3bf1xxx`, colour tables, etc. read as "beyond file."
- **Fix (permanent):** `av-cam-full.bin` = `nflasha3_unpacked[0x8e00:]` → clean VA base `0xc3441000`, covers
  `0xc3441000 .. 0xc4298200` (the whole address space). Carve:
  `python3 -c "open('.../av-cam-full.bin','wb').write(open('.../nflasha3_unpacked','rb').read()[0x8e00:])"`.
  **Use `av-cam-full.bin`, not `av-cam.bin`, for any VA ≥ 0xc3a811d8.** (File offset = VA − 0xc3441000.)

## 1. The components (code, all in-file)
| piece | VA | role |
|---|---|---|
| **stage table** | `0xc362997c .. 0xc3629bec` | **78 records × 8 B = {p0 Thumb ptr, p1 ARM ptr}** (p0 at the 8-byte boundary, p1 at +4) |
| **p0 thunk cluster** | `0xc3627xxx` | Thumb stage dispatchers — each branches on the **picture-effect class `ctx[0x23]`** |
| **p1 ARM region** | `0xc3bf14e0+` (step 0x14) | ARM-mode **config** code (geometry/strides/flags) — NOT per-step routines (§3) |
| **GEN executor** | `0xc363faa0` | generic stage: reads a descriptor, hands it to the dispatch interface |
| **interface thunks** | `0xc3676858+` | **PLT/virtual-call bank** — resolve a C++ interface method and tail-call it (§4) |
| **stage RTTI record** | `0xc3980abc` | C++ registration: `{method-ptrs 0xc395f4a5 / 0xc395f487, "Camera::Capture::Stage_NotifyDrawReview(Camera::Imaging::Image*)"}` |
| **masked-key lookup** | `0xc3bf0f14` / `0xc3bf14e0` | registry search by a masked key (bsearch idiom) |

## 2. The p0 thunk = per-stage picture-effect-class variant selector (intra-stage polymorphism) — CONFIRMED
**Two-level model (DeepSeek r4 correction):** the C++ driver first decides *which* stages run and *in what order*
(runtime, §4); then **each stage's p0 invoke-entry internally branches on the picture-effect class `ctx[0x23]`** to
pick the *concrete variant* of that stage, or returns `5` = **skip**. So `ctx[0x23]` is **intra-stage polymorphism**
(effect-class → impl variant) *inside* an already-selected stage — NOT the top-level step selector. Two forms:
- **simple** (e.g. step 2, `0xc3627f20`): `movs r1,#0x23; ldrb r1,[r1,r0]; cmp r1,#0; bne skip; bl 0xc363faa0` — run
  only for class 0, else skip.
- **jump table** (e.g. step 19, `0xc36281f6`): `cmp r1,#6; bhs skip; <6-entry table> add pc,r3` →
  class0→`0xc37ec57c`, class1→`0xc37deb92`, class2→`0xc37dfca2`, **class3→`0xc37e8ac4` (TBOX / Miniature)**,
  class4→`0xc37df2c0`, class5→`0xc363faa0`.

**Half of "what loads when" (the static half): the Picture-Effect class selects the concrete variant within each
stage** (the other half — stage order/enable — is runtime, §7). The full per-class × per-step matrix was extracted
(78 thunks). Direct stage→module bindings proven via the OPEN map (§6):
- `0xc37e8ac4` → `OPEN(tbox)` (codectype 0x17) — Miniature
- `0xc37ea898` → `OPEN(?codectype 0x45d8-wrapper)` 
- `0xc37ea42e` (dev/SPICA) → `Camera::Capture::SPICA 0xc37e9688` → `OPEN(spica)` (0x16)
- `0xc363faa0` (GEN) → descriptor → interface dispatch (§4)

## 3. The p1 ARM region = CONFIG half (geometry/flags), NOT routines — CONFIRMED (DeepSeek)
The p1 column steps exactly `0x14`, but that is **pointer arithmetic, not a routine table**: p1[5]=`0xc3bf1620` lands
on the 3rd instruction of a prologue beginning at `0xc3bf1614` (`mov ip,sp; push {..lr,pc}; sub fp,ip,#4`) — a call
there would corrupt the frame. The region is two ordinary ARM bodies:
- **Body A `0xc3bf15a8–1610`** — tagged-pointer list / flag RMW (bit0 tag set `and#1|orr`, clear `bic#1`,
  untag→deref→relink). Loop head at `0xc3bf0f14` (masked-key comparator).
- **Body B `0xc3bf1614–174c`** — buffer/segment **geometry**: `ceil(n/32)` word-counts, `×61 → ×488` strides,
  SRAM capacity clamps `0xc000`(49152)/`0x1800`(6144), writes **`ctx[0x18]=…, ctx[0x1c], ctx[0x20], ctx[0x24]`**.
  Never reads `ctx[0x23]`.
Binding: the GEN executor's callee does `ldr r0,[r4,#0x18]` — **exactly the field Body B wrote** — builds a 0x18-byte
descriptor and calls the module open/exec through the interface. So **ARM p1 CONFIGURES the step geometry; the module
handle flows `ctx[0x18]` → GEN → interface**; the *choice* of stage is the Thumb p0's `ctx[0x23]` branch.

## 4. The dispatch mechanism = C++ virtual/interface call — CONFIRMED
The "module-open" (`0xc3676858+`) is a **bank of PLT thunks**, each:
```
ldr r4,[pc,#imm]   ; literal @0xc3676b34 = 0xc3441000  (image base, used as anchor)
ldr r4,[r4,#0x14]  ; G = *(base+0x14) = 0xc34414d0     (the C++ interface singleton)
adds r4,#0xc0      ; → interface sub-struct
ldr r4,[r4,#0x18]  ; vtable slot +0x18 (next thunks use +0x1c,+0x20,+0x100,+0x10c…)
bx  ip             ; tail-call the resolved method
```
So stages are invoked **through a runtime C++ interface object** (`0xc34414d0`, reached via image-base+0x14), not by
static `BL`. `0xc3980abc` is the matching **RTTI/registration record** for a real stage
(`Camera::Capture::Stage_NotifyDrawReview`), method-ptr-then-mangled-name — the whole area is the
`Camera::Capture::Stage_*` framework.

## 5. Why the stage table is statically UNREFERENCED (the key anomaly, resolved)
Scanned the whole 15 MB image: **no absolute word points into `0xc362997c..0xc3629bec`; no MOVW/MOVT forms the table
VA (`#0x9a04`/`#0xc362`) OR its image-base offset (`#0x897c`/`#0x1e`); the entire `0xc3629xxx` page is referenced by
nothing; the p0 thunks are never a BL/BLX target.** This is **expected, not dead code**.

**Resolved (2026-10-17 runtime-reach dig, owner task #1):**
- **The interface object `0xc34414d0` is BSS** — in the static image it is ~all zeros (5/120 words non-zero, only at
  +0x04..+0x1c; the `+0xc0` region and the resolved slot `*(0xc34415a8)` are 0). So the vtable/registry is
  **runtime-filled**, not a static table. ⇒ the only pointer to the stage table lives in a **runtime object**.
- **Cross-core (candidate iv) is RULED OUT:** the table base `0xc362997c`, `0xc3629a04` and the interface `0xc34414d0`
  appear in **no other partition** (scanned nflasha1/2/7/10/12). The object is in **av-cam's own BSS**.
- **Installer chain located:** module header (`0xc344100c→0xc3441050` ARM) → `blx 0xc34412ac` (Thumb) = the **CRT/HW
  init** (relocates .data: copies 0x2d784 / 0x2074ac-byte blocks; MMIO `0xf40a1000`/`0xf5000064` = clock/DMA). The
  stage-registry install is NOT here — it runs later in the **C++ app-init tree**.
- ⇒ Net (candidate iii confirmed): the table is reached only via a **loader-relocated `.data` pointer** (av-cam does
  relocate .data at init) **or a C++ constructor** materializing the pointer at app bringup — never by any static code
  immediate. This is the exact boundary: **genuinely loader/runtime (IDA/trace-gated), not a coverage gap.**

## 6. The OPEN map (codectype → wrapper → stage), static (av-cam-full.bin)
`ExecuteOpenMSG` = `0xc3755340`, signature `(r0=this, r1=buf, r2=codectype)`. 10 direct OPEN sites, codectype in **r2**:

| codectype | module | OPEN wrapper | opened from |
|---|---|---|---|
| 0x01 | **apollo4** | `0xc37c1960` | 9 callers (0xc3733xxx + 0xc382xxxx cluster = many scenarios) |
| 0x0f | kknr | `0xc35a2e04` | dev zone |
| 0x11 | ? | `0xc35a2794` | dev zone |
| 0x16 | **spica** (develop/resize) | `0xc35a3e9c` | develop-core zone (`0xc37e9d80`, near `0xc37ea42e`) |
| 0x17 | tbox (Miniature) | `0xc35a36b8` | stage `0xc37e8ac4` (class 3) |
| 0x03/0x04/0x0e/0x1b | ? | `0xc37c1f50/28ec/3298/3d58` | 1 caller each |
| (0x45d8-wrapper) | ? | `0xc35a45d8` | stage `0xc37ea898` |

**Both apollo4 and spica ARE opened on the still path** (apollo4 widely, spica via develop-core) — yet gross-
corrupting their VLIW had no effect on full-res stills (E-earlier). Reconciled: they are OPENed/loaded, but the
per-pixel full-res develop arithmetic is HW/fixed-function; the VLIW modules act as config/orchestration there. The
only DSP VLIW that touches still LUMA per-pixel is **yknr** (ISO-gated NR). (Static corroboration of the grain ceiling.)

## 7. Net — the two-level model and the exact static ceiling
"What loads when" splits into two levels:
- **STATIC & complete (mapped):** per-stage **effect-class variant selection** — for each registered stage, the p0
  invoke-entry's `ctx[0x23]` branch (all 78 enumerated) picks the concrete impl/module or skips (=5). Plus the C++
  method/RTTI records (statically referenced, e.g. `0xc3980abc`), the OPEN map (§6), and the ARM p1 geometry config.
- **RUNTIME-only (genuinely IDA/trace-gated, not a coverage gap):**
  1. the **stage order/sequence** — a C++ driver decision through the interface at `0xc34414d0`, not a walk of the
     `0xc362997c` table;
  2. the **enable/policy set** (which stages are active for a given shot) — a separate runtime input the `ctx[0x23]`
     branches don't encode;
  3. ~~the reach mechanism to the table~~ — **RESOLVED (§5):** object-held in av-cam's own BSS (`0xc34414d0`),
     installed by a C++ ctor / loader-relocated .data at app bringup. Cross-core ruled out. The only sub-unknown left
     is *which* C++ ctor does the install (deep in the app-init tree, past the CRT init at `0xc34412ac`).
- **One unresolved structural point:** whether the uniform-0x14 p1 column is segment/descriptor *data* or an
  interworking ARM counterpart — needs the full `0xc3bf14e0..0xc3bf1bac` body. (Low priority; p1 is proven consumed as
  data, §3.)
Note `*(0xc3441000) = 0xe28ff028` = `add pc,pc,#0x28` (a PIC jump trampoline at the module header); `*(base+0x14) =
0xc34414d0` = the resolved interface object the whole dispatch hangs off. Everything else in the router layer is mapped.

## Tools / cross-refs
- Binary: **`.../nflasha3_unpacked_unpacked/av-cam-full.bin`** (VA base `0xc3441000`, offset = VA − base). capstone
  ARM `CS_MODE_ARM` for `0xc3bxxxxx`, `CS_MODE_THUMB` for the thunks. DeepSeek `dsq.py` (3-round decode, sessions in
  `ds_prompt{,2,3,4}.txt`).
- See `02-capture-pipeline.md` C-PIPE-026/027/028 (components) and new C-PIPE-029/030; `04-dsp-modules.md` (modules);
  `grain-roadmap.md` §7 (grain ceiling); `full-atlas-build.md` (atlas state).
