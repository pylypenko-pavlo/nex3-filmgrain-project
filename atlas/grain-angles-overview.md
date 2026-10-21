# Grain injection — global angles & status (2026-10-13)

One-page strategic map of **every** grain-injection angle we've explored, its status, why, and the
remaining hope. Companion to `dsp-grain-scope.md` (details) and the E-records (`06-experiment-log.md`).
Written at the pause after both offline research threads (module-grow, VLIW, scalar-16) converged.

## The core constraint (what the delivery path actually gives us)
Delivery = **/setting module edit of `sa_yknr`** (reversible, PROVEN on camera). It gives us exactly:
- **file-data edits** — unlimited within the **~53 KB senser writeFile limit** (module is 53508 B);
- **VLIW bundle edits** — into existing free lanes, **no code space needed**;
- **16 bytes/core of scalar code** — the ONLY genuinely-dead executable space (the per-core shutdown
  stub at `chunk+0x08`; Probe S proved it reaches the JPEG).

Pixel-write → JPEG is PROVEN (Probe S white grid). The whole grain problem reduces to: **get a per-pixel
noise VALUE and ADD it to luma, within those three means.** Everything below is an attempt at that.

## Angle table
| # | angle | mechanism | status | why / blocker |
|---|---|---|---|---|
| A1 | ARM pixel write | CPU1 av-cam writes the canvas | ☠ **DEAD** | canvas is read-only for CPU1; data-aborts both aliases (E-0074, 7 flashes) |
| A2 | scalar full-tile loop | 72 B xorshift loop in dead space | ☠ **DEAD** | only 16 B dead/core; placement over the engine table HANGS (E-0075/76); module-grow blocked (no in-module loader, table frozen, file can't grow) |
| A3 | scalar ≤16 B clever | fit grain into the 16 B stub | ☠ **DEAD** | tightest loop = 18 B; byte 17 = live `0x4000` stack-init const → 1 instruction short. + entropy wall (self-dither has no texture) |
| A4 | VLIW inject `op7 r21→r19` | add ±N in a free bundle lane | ✓ **inject free** | no code-space cost; needs a register holding ±N (→ A5/A6/A7) |
| A5 | VLIW self-dither | mangle the pixel's own bits | ☠ **DEAD** | 13-bit slot has NO immediate (only r31=0) → can't build a bounded ±N amplitude |
| A6 | VLIW DMA-LUT (new stream) | op5 ptr + op3 reads baked noise | ☠ **blocked** | baking + DMA-ing a NEW stream needs scalar engine-DMA setup = the 16 B ceiling |
| A7 | VLIW DMA-LUT **piggyback** | ride the EXISTING reciprocal-LUT DMA | ❓ **UNEXPLORED** | edit LUT data (file, no code) + VLIW op3-read + op7-add (free lanes). Obstacles: op5 ptr needs an address w/o immediate; overwriting the recip-LUT breaks normalization. **Only path to REAL grain without the ceiling** |
| A8 | host routine in another `sa_*` | bigger dead exec space elsewhere | ❓ unexplored | a different module's pass may not reach the output tile; reachability unknown |
| A9 | firmware / boot-level | the external DSP loader | ✗ out of scope | not achievable with an offline module edit |

Legend: ☠ dead (proven) · ✓ works · ❓ open/unexplored · ✗ out of scope.

**UPDATE (E-0077, 2026-10-13, on camera):** the VLIW chain probe (A4) was run — `op7 r19→r19` at bundle
`0xce88` produced **NO visible effect** across 3 high-ISO shots (ISO 12800–16000; a flat mid-grey wall
stayed mid-grey, not clipped). So r19 at the P4 finalize bundles (`0xce80/0xce88`) is **not the output
per-pixel luma** — our static VLIW luma model has a gap, not closable without a VLIW emulator. This
**demotes A4 to ☠ at the known insertion points** and **undercuts A7** (it relied on op3+op7→r19 at those
same lanes). Any VLIW route now first needs the TRUE output-luma bundle found (a camera probe ladder or an
emulator) — low confidence. Positive side-finding: p3 is high-ISO-capable (no reboot at ISO 16000).

**UPDATE (external expert + ISA verification, 2026-10-13):** an external expert cracked the 16-byte puzzle
— but for an **ARM/Thumb-2** machine. Verified against the REAL SA-DSP scalar ISA (sadis decode tables +
corpus): **none** of the enabling idioms exist. The instruction is strictly 2-operand (`opcode.rm.rn`, no
shift-amount field) → **no barrel-shifter operand** (`add rd,rn,rm,asr#k` is unencodable; each fused ARM op
= 2–3 SA-DSP ops); **no saturating add** (clamp needs explicit cmp+branch); **no RPT/block**; byte ops step
by 1 and pre-decrement is store-only; and crucially **shifts do NOT set the flag**, so the counter-free
`lsls→Z` loop-end trick has no equivalent (needs `and`+`cmp`). Real floor: the tightest honest aperiodic
loop (shift-diffusion `ptr ^ (ptr>>k)` DOES fix periodicity) = **38 bytes / 19 instr** (no clamp), ~46 with
clamp — **2.4–2.9× over the 16-byte slot**. The two-hook split (V5) also fails: **no second dead slot** per
core, and the per-tile LUT-apply is itself a >16-byte loop. **→ A3 and V1–V5 are CLOSED on hard ISA facts**
(the entropy wall was real-but-fixable; the code-space wall is absolute). Scalar grain is definitively dead;
3rd independent confirmation. Value gained: the periodicity wall was refuted (shift-diffusion), and the real
floor is now known (38 B, not the earlier 18 B estimate — our ISA is stricter).

## Remaining hopes (ranked)
1. **A7 — DMA-LUT piggyback.** The only route to *real* grain that sidesteps the 16 B ceiling (data edit
   + VLIW ops, no scalar code). Uncertain — the op5 stream-pointer and the normalization-LUT reuse are
   unproven. **This is the one worth a focused offline RE push next window.**
2. **VLIW chain probe** (`sa_yknr_vliw_probe.bin`, built) — camera test: does `op7 r19→r19` at bundle
   `0xce88` reach the JPEG (the old PoC at `0xce80` showed nothing)? Gates ALL VLIW work. Cheap, reversible.
3. **More 16-byte scalar variants** (A3 revisited) — see next section (owner asked to keep this alive).
4. **A8 — other-module host.** Lowest confidence.

## More 16-byte variants to try (per owner, 2026-10-13)
The scalar-16 verdict was "min per-pixel loop = 18 B, exactly 1 instruction (2 B) short, + no entropy."
Concrete ways to find those 2 bytes and/or dodge the entropy wall — the next scalar angles to attempt:
- **V1 — kill the displaced instruction.** The stub currently spends 1 slot replaying the hook's displaced
  `add sp,#0x50`. Hook a point where the replaced instruction is DEAD/redundant (or reconstruct its effect
  inside the return path) → saves 1 instr = 2 B → the loop fits 16 B.
- **V2 — a 16 B slot with 2 more trailing dead bytes.** Re-map every core's stub boundary and the other
  sub-images for a dead slot that has ≥18 B before the first live byte (scalar-16 only pinned the first one).
- **V3 — shorter base-pointer setup (<3 instr).** Is a usable pointer register already live at the hook
  (besides r13)? The tightest build still spent setup on it; a reusable base saves instructions.
- **V4 — a hardware block/fill or hardware-loop idiom.** If the SA-DSP scalar ISA has a memset-like or a
  zero-overhead hardware loop counter, the per-pixel loop overhead collapses → real loop in ≤8 instr.
- **V5 — two-stub split.** Hook TWO points per core, each a 16 B stub doing half the routine (needs a
  second dead slot per core within branch range) → effectively 32 B.
- **Entropy caveat (applies to all):** even if a loop fits 16 B, a 1-op self-dither still won't look like
  grain. A real noise source needs either the evolving xorshift (bytes we don't have) OR a free noise
  stream (→ A7). So V1–V5 unlock *space*, not *entropy* — pair with a cheap stream source.

## Camera probes queued (next camera session, owner present)
All reversible /setting, high-ISO shot, revert = restore stock:
- `sa_yknr_vliw_probe.bin` (md5 `7d1bb24e…`) — does `0xce88→r19` reach the JPEG?
- `sa_yknr_probe_freeram.bin` (md5 `e12806a4…`) — is DSP `0x5000` benign RAM?
- op1/op2 discriminator ladder (only if the VLIW probe passes).
Pre-flight: p3 must be high-ISO-capable (`current_p3`, not EXP-11) — grain/VLIW only runs at high ISO.

## Bank-able wins (independent of grain)
- **Colour lineup** (6 films → style slots) — fully reachable, reversible Backup, `colour-slots-lineup.md`.
- **Delivery (/setting) + scalar pixel-write** — PROVEN, reversible.
- **Per-style grain design** (`style-grain-coupling.md`) — a 2-edit plan, ready IF grain ever lands.

## Honest standing verdict
Full additive **grain** via the `/setting` path is blocked on every proven route; it survives only as (A7)
the unexplored DMA-LUT-piggyback and (V1–V5) the not-yet-exhausted 16-byte-space tricks — both uncertain.
The **colour** half of "X100 for the poor" is done and shippable. Grain is the documented hard frontier.
