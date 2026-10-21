# Atlas: how to read it

This directory is the working research log for the NEX-3N film-grain project. It was written while the
work was happening, dated, and it keeps the dead ends next to the results on purpose. The curated summary
of what was found is the root `README.md`; read that first. Come here when you want the derivation, the
address, the experiment that proved a claim, or the reason a path was abandoned.

The atlas is organised around two record types, claims (`C-<AREA>-<NNN>`) and experiments (`E-<NNNN>`),
each with a status (`verified-hw`, `verified-code`, `hypothesis`, `refuted`) and a scope (which bodies it
was checked on). The schema, the area codes and the rules are in `00-index.md`. If you grep for an ID you
get the full record.

Two things you will meet in the log. 'The owner' is me, the author. 'Agent', 'DeepSeek', 'opus', 'sonnet' and
'fable' are AI assistants I worked with; some pages are their raw output and a few experiment notes quote
me in Russian. None of it was rewritten after the fact.

## Where things are

Platform and pipeline

- `01-system-map.md`: chips, cores, partitions, who loads whom.
- `02-capture-pipeline.md`: the path of a still from sensor to card.
- `capture-orchestrator.md`, `av-cam-executors.md`: the stage router in `av-cam` and what each
  executor actually is (HW block, DSP module, cross-LSI call).
- `03-control-flow.md`: how a menu setting travels through Backup to the ISP/DSP descriptors.
- `04-dsp-modules.md`: catalogue of every `sa_*.bin` and `idt_cam` overlay.
- `sa-dsp-isa.md`: the SA-DSP scalar ISA and the undocumented VLIW `run_engine` coprocessor.

Grain, the route that shipped (Linux side)

Read these in order; they are the stage runbooks of the in-camera grain hook, from loader acceptance to a
grained JPEG coming off the camera.

- `grain-linux-route-safety-2026-10-19.txt`: why a boot preload is brick-capable and what a recovery net
  would need to look like.
- `grain-linux-stage0-2026-10-19.txt`, `grain-linux-stage1-runbook-2026-10-19.txt`,
  `grain-linux-stage2-runbook-2026-10-20.txt`: the dynamic loader accepts our object, the `env.txt`
  preload boots, the `\updater\mode` recovery-net analysis.
- `grain-linux-stage4a-design-2026-10-20.txt`, `grain-linux-stage4b-design-2026-10-20.txt`: interposing
  `Fsys_Close`, the capture gate, and why the hardware JPEG codec cannot be used from the shim.
- `grain-linux-stage4c-*`: the freestanding software codec, the streaming callback shim, the boot OOM,
  the dead `rename`, and finally `grain-linux-stage4c-WORKS-auto-landing-2026-10-20.txt`.
- `grain-linux-stage4c-STYLE-retuned-ultramax-2026-10-21.txt`,
  `grain-linux-stage4c-SPEED-baked-tile-2026-10-21.txt`,
  `grain-linux-stage4c-SPEED-fastpt-validated-2026-10-21.txt`: tuning the look to real UltraMax 400
  scans and getting a shot down to about 16 s.
- `grain-linux-stage4c-ONCAMERA-run-log-2026-10-21.txt`: the shim's own log from the two shots on the
  camera, the numbers behind "about 16 s per shot".
- `grain-linux-BRICK-INCIDENT-and-hw-recovery-2026-10-21.txt`: how the development body was bricked,
  why that is not recoverable in software, and the hardware boot-mode strap that is the only way back.
- `grain-linux-brick-recovery-2026-10-20.txt`: the loader-level analysis of every recovery door.

The shim source itself lives in `../code/grain-shim/`.

Grain, the route that was closed (DSP side)

The first attempt was to inject grain inside the SA-DSP imaging path. It is fully explored and blocked
by hardware; these pages are kept because they are most of what is known about the VLIW engine.

- `grain-RESTART.md`: the state of that route when it was stopped, and the reasons.
- `grain-sftfcs-confirmed.md`: the Soft Focus module, its channel map, what it does and does not touch.
- `grain-roadmap.md`, `pbe-engine-map.md`, `luma-stage-yknr.md`, `grain-chroma-solution.md`,
  `engine-command-table.md`, `grain-injection-design.md`, `grain-vliw-injection-plan.md`: the PBE and
  YKNR engine maps, the VLIW substitution experiments and the injection designs.
- `grain-angles-overview.md`, `grain-wide-analysis.md`, `grain-via-effects.md`, `grain-codecave.md`,
  `scalar16-grain-ideas.md`: the other angles that were weighed.

Colour, tone, settings store

- `05-delivery-and-safety.md`: what can be written where, how to roll back, the tools. Read this before
  writing anything to a camera.
- `style-grain-coupling.md`, `grain-luma-response.md`: how Creative Style colour interacts with grain.
- The colour matrices, hue tables and tone curves themselves are documented in `../notes/` and the
  designed values are in `../data/`; the root README summarises the measurements.

Experiments and open questions

- `06-experiment-log.md`: every on-camera experiment with its E-ID.
- `07-open-questions.md`: what is still unknown, ranked.
- `_extract/`: raw per-source extractions, working material rather than authoritative claims.

Anything in this directory not listed above: `00-index.md` has the schema and the rest is the raw log, in
file-name order.

## Conventions

Addresses are `av-cam` virtual addresses (base `0xc3441000`) unless prefixed; `idt_cam` offsets are file
offsets inside the module. Everything is checked on one body, a NEX-3N at firmware 1.00, unless a claim's
`scope` line says it was confirmed on another. The repo ships no firmware images or dumps; tools that
need them read your own files, see the root README.

Some entries read like notes to a future session ("resume here", "next task") because that is what they
were. They were left as written rather than tidied, so that what was tried and when stays visible.
