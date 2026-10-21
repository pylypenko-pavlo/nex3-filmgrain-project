# Dev-environment & migration to M4 Pro 48 GB (2026-10-15)

Decision (owner): **move NEX-3N development from the M1 Pro / 32 GB to an M4 Pro / 48 GB.** This note is the
hand-off: what to set up, what was learned about local/remote LLMs for the VLIW work, and the carry-over tool.

## Why move
- M1 Pro 32 GB is **swap-bound** for local LLMs: loading qwen3:30b (18 GB Q4) with ~12 GB free pushed the
  machine to 14 % free and inference crawled (>10 min for one short decode).
- M4 Pro 48 GB: no swap on a 30 B, ~1.4× memory bandwidth (≈273 vs 200 GB/s) + faster cores ⇒ ~2–4× effective
  inference speed, and headroom for 70 B Q4 (~40 GB) that the M1 can't hold.
- Caveat kept honest: for the **hard** VLIW reasoning (Phase 0 GO/NO-GO), frontier-model quality matters more
  than local speed — the M4 helps local throughput, it is not the lever that cracks the VLIW.

## Local / remote LLM assessment (tested on M1 Pro, 2026-10-15)
- **qwen3:30b (MoE, ollama)** — decode-a-VLIW-bundle test (5 bundles, ground truth from the decoder below):
  the model **reasoned the bit-math correctly** (`S0=(v>>52)&0xFFF`, `op=(slot>>10)&7`, …) but **did not emit
  parseable output** (rambled prose instead of JSON, even with `/no_think`) and was swap-slow. Fix for a retry:
  ollama **`--format json`** / structured-output + more RAM (the M4). Capability present, reliability poor.
- **DeepSeek v4.1 Flash** — "free in OpenCode" only: **OpenCode CLI not installed here**, and the raw DeepSeek
  API key returns **Insufficient Balance**. Not reachable from an agent session directly. To use it, run it
  inside OpenCode by hand; a self-contained brief can be prepped (see `DEEPSEEK-sftfcs-grain-module.md` for the
  format).
- **Takeaway:** the VLIW *decode* is deterministic (the Python tool below — no LLM needed). The VLIW *reasoning*
  (free stream port? editable add-slot?) wants a frontier model. A local 30 B adds little to either; don't run
  it overnight on this task.

## M4 setup checklist (to resume work)
1. **Repos:** clone `nex3-filmgrain-project` (this atlas, github pylypenko-pavlo) + copy `~/nex3n-dump/` (modules,
   `work/filmgrain/` builders/probes, `pmca/`, saasm/saemu/sadis under `code/isa`, `code/grain`).
2. **Camera toolchain:** `pmca` venv (`work/pmca/venv`, needs `pyusb`+`axmlparserpy`; run with
   `PYTHONPATH=…/work/pmca`), libusb (`/opt/homebrew/lib/libusb-1.0.dylib`), askpass GUI (`askpass.sh`),
   `sudo -A` for USB. Deliver = `deliver_sftfcs.py <bin>`; revert = `deliver_sftfcs_revert.py`.
3. **Local LLM (optional):** `ollama pull qwen3:30b` (or a 70 B Q4 now that 48 GB fits); always drive with
   `--format json` for scoreable output.
4. **⚠️ FIRST ACTION — camera is unsafe:** it was left with the `vizsram` probe loaded **and crashed** (USB
   down). Power-cycle, then **revert `sa_sftfcs` to stock** (`deliver_sftfcs_revert.py`, Backup `0x00bd0002`
   byte 445→0) before anything else.
5. **Resume at:** `grain-vliw-injection-plan.md` Phase 0.1 on PBE (`sa_pbe_work`), using the decoder below.

## Carry-over tool — SA-DSP VLIW bundle decoder (deterministic, verified)
64-bit LE word; `S0`=bits[63:52]; `S1..S4`=13 bits each ([51:39],[38:26],[25:13],[12:0]); each slot =
`op`[12:10].`a`[9:5].`b`[4:0]. op: 0 move · 1 pack/shift · 2 undecoded · 3 read-stream · 4 mul · 5 AGU/store ·
6 clamp · 7 add. NOP `0x1f70fb87dc3ee1f7` → S0=0x1f7, all slots `op0 a15 b23`. Verified on `sa_pbe_work`
(bundle `f8285bc2…` → S4 `op7 add a30 b2`; `f4aa3cd1…` → S1/S2 `op5 store`).
```python
import struct
NOP=0x1f70fb87dc3ee1f7
OPN={0:'move',1:'pack/shift',2:'(undec)',3:'read-stream',4:'mul',5:'AGU/store',6:'clamp',7:'add'}
def decode(w):                      # w = 64-bit int
    S0=(w>>52)&0xFFF; sl=[]
    for sh in (39,26,13,0):
        s=(w>>sh)&0x1FFF; sl.append(((s>>10)&7,(s>>5)&0x1F,s&0x1F))  # (op,a,b)
    return S0,sl
def bundles(path):                  # iterate (file_off, word) over a module's 8-byte words
    f=open(path,'rb').read()
    for o in range(0,len(f)-8,8):
        yield o, struct.unpack_from('<Q',f,o)[0]
# find microcode: runs of NOP-adjacent words; real compute bundles have op in {4,5,6,7}.
```
(Working copy: `~/nex3n-dump/work/filmgrain/vliw_decode.py`.)

## Tooling — DeepSeek v4.1 Flash-free via OpenCode (reliable method, don't lose this)
Installed OpenCode `1.19.1` (`brew install sst/tap/opencode`). It exposes **free frontier models** through the
`opencode` provider (opencode-zen), e.g. **`opencode/deepseek-v4.1-flash-free`** — usable WITHOUT the raw
DeepSeek API key (which has no balance). `opencode auth login` → provider `opencode` (not `deepseek`).
- **Do NOT script `opencode run`** — it renders to a TUI and emits nothing to a pipe/redirect (empty capture).
  (A pseudo-tty via `script -q /dev/null opencode run …` works for one-shots but is fragile on long prompts.)
- **Reliable automation = the headless server + HTTP API:**
  ```
  opencode serve --port 4096            # headless; OpenAPI at http://127.0.0.1:4096/doc
  POST /session                          -> {id}
  POST /session/{id}/message             body {"model":{"providerID":"opencode",
                                                        "modelID":"deepseek-v4.1-flash-free"},
                                                "parts":[{"type":"text","text":"<prompt>"}]}
                                         -> {info, parts:[{type:"text",text:...}]}  (synchronous)
  ```
  Reuse one session id for multi-turn context (persists). `/api/session/{id}/compact` or roll to a fresh
  session to stay under the **200k** context window.
- **Quality gate (2026-10-15):** on a 5-bundle VLIW-decode test with deterministic ground truth,
  `deepseek-v4.1-flash-free` scored **5/5** in ~8 s and traced the PBE output store (r15←clamp, port-24
  stream, PROVEN-vs-HYPOTHESIS, camera tests) at a genuinely useful level — far above local qwen3:30b (which
  reasoned the bit-math right but rambled instead of emitting JSON, and swap-crawled on the M1).
- **Overnight runner:** `~/nex3n-dump/work/filmgrain/overnight_vliw.py` — drives the API in a loop until
  08:00, `caffeinate -i -s` (awake, no display), session-rolls every 12 turns (200k cap), rate-limit→pause /
  hard-fail→stop+uncaffeinate, appends to `overnight-vliw-report.md`. Staged prompts: Phase 0 (decode/port
  audit/add-slot) → Phase 1–4 (edit list, proof test, stream feed, luma mod) → a pool of open-map questions
  (Q-17 op3 ports, op1/op2 decode, S0 header, Q-3/Q-20 pipeline). Context brief + decoder:
  `context_brief.md`, `vliw_decode.py`.

## State at migration
- Colour half: SOOC-shippable, untouched.
- Grain: both module-scalar routes closed (E-0085 PBE, E-0086 sftfcs); live path = VLIW noise-stream injection
  (`grain-vliw-injection-plan.md`), gated on Phase 0.
- Camera: `vizsram` loaded + crashed → **revert pending** (see step 4).
