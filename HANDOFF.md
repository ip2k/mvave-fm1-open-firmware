# Hand-off package — M-VAVE FM-1 open firmware

Written 2026-09-06 at the end of the research session that created this
repository, so a fresh Claude project (or a human) can continue without the
original conversation. Read this first, then `README.md`, then `docs/`.

## 1. Where things stand

- **Owner:** Sean (GitHub `ip2k`). Works from a MacBook with Claude Desktop /
  Claude Code; has **one FM-1** on his desk (do not brick it) and has downloaded
  the official updater disk image **`M-UPGRADE-FM1*.dmg` into `~/Downloads`**
  (that updater embeds **V14**, not V15; V15 is only on the CDN, docs/02 §1).
- **This repository** is the research output: nine documents, three tools, one
  research log, plus bench session 1 (`notes/2026-09-06-bench.md`): the unit
  answers the identity query as `FM-1_015`, V15 is unpacked and diffed against
  V14. Nothing has been written to the device. No custom code has ever run on
  any FM-1 (by anyone).
- **Where the repo lives now:** `~/Developer/mvave-fm1-firmware` on the
  owner's MacBook, branch `main`, remote `ip2k/mvave-fm1-open-firmware`. Moved there on
  2026-09-06 from the orphan branch `claude/mvave-fm1-open-firmware-ly2w6u` of
  `ip2k/busybar-dual-timer`, which the cloud session used because its GitHub
  integration could not create repositories. Delete that branch once a remote
  exists — see `README.md` → "Repository history".
- **Unrelated to the BUSY Bar project.** Do not mix the two.

## 2. The ten facts that matter

1. SoC = **JieLi AC791N** (WL82), custom **pi32v2** CPU, one core used at
   240 MHz, 578 KB SRAM, 1 MB flash (probably in-package), XIP from
   `0x02000000`, RAM at `0x01C00000`. Marking `C156211-11B8`, LQFP48.
2. Stock firmware = JieLi AC79 SDK (FreeRTOS-derived kernel, closed `.a` libs
   for BT/audio/fs/cpu) + M-VAVE glue + **Google msfa (Dexed) FM engine**.
   Verified here: msfa algorithm table at `0x8C46C` (V13) / `0x8CBCC` (V14) of
   `app.bin`, with the Dexed-family fix in algorithms 4 and 6.
3. Update = **USB-MIDI SysEx**, device-pull protocol, **CRC16 only, no
   signature**, chip key `0x980F` in the package. Two stages: verifier in the
   app → reboot into a RAM OTA loader (`4D4A:4155`) → flash write → reset.
4. **Rebuilt packages are rejected** by the app-side verifier unless their
   version identity is bumped: AL-255's 2026-07-21 probes failed at an
   unexplained check, but Echomatter (AL-255 PR #2, 2026-09-04) installed a
   V15-derived package identifying as `FM-1_016` through the stock path, ran
   it, and rolled back to stock V15 with the corrected Linux client. Stock
   packages, including downgrades, pass.
5. **No proven recovery path**: single flash bank, no debug pads/buttons,
   mask-ROM USB boot never demonstrated on an FM-1. AL-255's verdict:
   NO-GO for non-stock flashing. This is the gate for everything. The
   `USB_KEY` dongle that should open it is specified and implemented
   (docs/10, `dongle/`), not yet tried.
6. Most promising recovery: JieLi **`USB_KEY`** (`0x16EF` bit-banged on D+/D−
   at ~50 kHz at power-up, ACK = both lines low 1–2 ms, then SOF clock
   detection) → mask-ROM "UBOOT1.00" mass-storage mode → `jl-uboot-tool`
   with its `wl82loader.bin` (`0x1C02000`) or vendor `isd_download`. The two
   kagaimiq docs disagree on which line is clock; try both.
7. Toolchain = JieLi's closed **Clang/LLVM 4.0.1** fork (`pi32v2` backend),
   Linux build available from `pkgman.jieliapp.com`; AL-255 built C++11 with
   it. No Rust, no GCC/LLVM upstream, no JS runtime.
8. Vendor SDK `fw-AC79_AIoT_SDK` (Gitee; GitHub mirrors) is Apache-2.0 with a
   public register map `WL82.h`, linker scripts, `demo_hello`, flashing tools,
   `wl82loader.bin`, a JTAG/debug-TAP folder, and datasheets; ~110 closed `.a`
   libraries per CPU. JieLi's `fw-Bootloader` (Apache-2.0) targets wl82.
9. **schwung-movy is not portable** (TS + Rust on a quad-A72 Linux box). Reuse
   its *design*: 8-knob parameter pages (FM-1 has 8 knobs), Move-style
   sequencer semantics, `seq-core` as a desktop test oracle.
10. USB IDs: normal `4C4A:C755` ("FM-1 Midi" + "FM-1 Audio" UAC1), OTA
    `4D4A:4155`. Identity query `F0 00 32 45 00 00 00 40 7F F7` → 41-byte
    reply `F0 00 32 45 58 01 00 00 23 4D 5A 44 …` (verified; the owner's unit
   decodes to `FM-1_015`, see docs/03 §2).

## 3. Decisions taken

- Target **L1** first (open application on the vendor SDK), then open
  bootloader (L4), then blob removal (L2); an open compiler (L3) is out of
  scope unless a contributor wants it. See docs/05.
- **Recovery before any flash.** Bench work is read-only until docs/07
  Phase 2 is done. Rules of engagement in docs/07 §4.
- Do not port Movy; reimplement in C with Movy as the reference (docs/06).
- Never commit vendor firmware (`.fwsc`, `app.bin`) or the JieLi toolchain;
  `.gitignore` enforces the first.
- Confidence marks **[verified]/[reported]/[inferred]** in all docs; keep them
  honest (the owner's other projects work the same way).
- License MIT for our material.

## 4. Open questions (ranked)

1. Does `USB_KEY` reach the AC791N's mask ROM through the FM-1's USB-C port,
   and with which clock/data polarity and power sequence?
2. What does the step-1 verifier compare that makes rebuilt packages fail?
3. Knobs: which of the eight are encoders and which pots (stock scans 2
   encoders + 2 ADC channels)?
4. Flash: in-package or discrete, exact size (JEDEC ID)?
5. AC791N variant and pinout; UART and debug-TAP pins reachable on LQFP48?
6. Does the SoC enumerate on USB with the power switch off (needed for the
   `USB_KEY` attempt)?
7. Any GPL-only Dexed code in the stock image (licensing lever)?

## 5. Immediate next actions (in order)

1. ~~Move the repo.~~ Done 2026-09-06: `~/Developer/mvave-fm1-firmware`,
   pushed to `ip2k/mvave-fm1-open-firmware`.
2. ~~docs/09 §1–§3.~~ Done 2026-09-06 (`notes/2026-09-06-bench.md`).
3. Power-switch-off enumeration test (docs/09 §2, last paragraph) and the
   case-open photo list (docs/09 §5).
4. Build the `USB_KEY` dongle from docs/10 (CI publishes the UF2), then run
   its bench procedure (docs/10 §6). Previously: decide on a `USB_KEY` dongle (buy JieLi's "USB Updater" dongle or build one
   on an RP2040) and, ideally, a JL_AC79_DevKit or a second FM-1 to rehearse on.
5. ~~Contact aroum and AL-255.~~ Done 2026-09-06: AL-255 PR #3 (V15 package),
   comments on their PR #2 and issue #1, aroum issue #2 (docs/04). Watch those
   threads for replies before posting anything further.

## 6. Reference material already gathered (clone these locally)

| Repo | Commit inspected | Why |
| --- | --- | --- |
| `aroum/fm1-custom-fw` | `d08360f` 2026-08-21 | updater analysis, photos, untested flasher |
| `AL-255/FM-1-RE` (`main`) | `95eca84` 2026-08-16 | disassembly, protocol, safety, firmware images V13/V14 |
| `AL-255/FM-1-RE` (`with-custom-firmware`) | `628fcaf` 2026-08-02 | experimental pi32v2 firmware, package builders, Synth_Dexed port |
| `kagaimiq/jielie` | `1657d25` 2024-09-15 | JieLi docs: ISA, USB_KEY, formats |
| `kagaimiq/jl-uboot-tool` | `adb3f18` 2025-03-16 | UBOOT dumper/flasher, `wl82loader.bin` |
| `kagaimiq/jl-misctools` | `0a5b12d` 2025-02-20 | `fwunpack_newfw.py` |
| `jeffreywugz/fw-AC79_AIoT_SDK` (`release/AC79NN_SDK_V1.0.3`) | mirror | vendor SDK: `WL82.h`, `cpu/wl82/tools`, datasheets |
| `DimaDake/schwung-movy` | `5627d51` 2026-09-05 (v0.31.0) | design reference only |

Web pages that were **blocked** from the research sandbox and still need a
human read: cuvave.com product page, the user manual PDF, synthanatomy.com
articles, fwradar.com history, elektronauts/gearspace/reddit threads,
fm1-editor.com, kagaimiq.github.io (use the repo), gitee.com (use mirrors),
madushan.caas.lk blog post.

## 7. Kick-off prompt for the new Claude project

Paste this as the first message of the new project (adjust paths):

> This project is the open-source firmware effort for the M-VAVE FM-1 FM
> synthesizer. The repository (`~/Developer/mvave-fm1-firmware`) contains a
> completed research phase: read `HANDOFF.md`, then `README.md`, then
> `docs/01`–`09` and `CLAUDE.md`. Rules: the FM-1 on my desk is the only unit;
> nothing may be flashed or sent to it beyond the read-only identity query
> until recovery is proven (docs/07). Today's tasks: (1) run
> `docs/09-first-session-checklist.md` §1 to extract and analyse the V15
> firmware from `~/Downloads/M-UPGRADE-FM1*.dmg`; (2) §2–§3 USB descriptors and
> identity query with the FM-1 plugged in; (3) write results to
> `notes/<date>-bench.md` and update the open questions in `docs/01` §6 and the
> version table in `docs/02` §1. Keep the [verified]/[reported]/[inferred]
> marks honest.
