# Open firmware for the M-VAVE FM-1

Research toward a fully open-source firmware for the M-VAVE (Cuvave) **FM-1**, a
~€70 battery-powered six-operator, 12-voice FM synthesizer with 27 silicone keys,
a 1.54" colour TFT, USB-C (MIDI + audio), BLE-MIDI and a 3.5 mm MIDI input.

> **Status (2026-09-06): research phase.** Nothing has been flashed, the device
> has not been opened or probed by this project yet, and no custom code has ever
> been shown to run on an FM-1 by anyone. Start with
> [`docs/05-open-source-feasibility.md`](docs/05-open-source-feasibility.md) for
> the verdict and [`docs/09-first-session-checklist.md`](docs/09-first-session-checklist.md)
> for what to do with the device on the bench.

## The short version

- **The chip is a JieLi AC791N** (JieLi's "WL82" family) running JieLi's own
  Blackfin-derived **pi32v2** CPU core, executing in place from a 1 MB flash
  image. It is the same platform JieLi sells for Wi-Fi speakers and story
  machines. The board is silkscreened `DX7 MB V07`.
- **The stock synth engine is Google's msfa, the Dexed core.** Verified in this
  repo: the 32-entry FM algorithm table from `fm_core.cc` sits byte-for-byte at
  offset `0x8C46C` of the V13 application image (with the Dexed-family fix for
  algorithms 4 and 6). The factory bank is reportedly the DX7 ROM1A cartridge.
- **Updates are plain USB-MIDI SysEx with CRC16 and no signature.** Two prior
  projects, [aroum/fm1-custom-fw](https://github.com/aroum/fm1-custom-fw) and
  [AL-255/FM-1-RE](https://github.com/AL-255/FM-1-RE), have reverse-engineered
  the protocol byte-for-byte, disassembled two firmware versions and even built
  an experimental pi32v2 firmware blob.
- **Nobody has run custom code on an FM-1.** The stock updater's on-device
  verifier refuses rebuilt packages at a check nobody has explained, and there
  is **no proven recovery path**: one flash bank, no debug pads, no recovery
  button, and JieLi's mask-ROM USB boot mode has never been demonstrated on
  this device. AL-255's standing verdict is *NO-GO for non-stock flashing*.
- **"Wholly open source" is bounded by JieLi.** The compiler is a closed
  Clang/LLVM 4.0.1 fork with a proprietary pi32v2 backend, and the vendor SDK
  links closed `.a` libraries (Bluetooth controller and stack, audio server,
  filesystem, even `cpu.a`). The SDK sources, register headers and a
  replacement bootloader are Apache-2.0. The realistic first target is *an open
  application on the vendor SDK*; blob removal and an open toolchain come later.
- **schwung-movy cannot be ported, but its design can.** Movy is
  TypeScript + Rust running inside Ableton Move, a quad-core Cortex-A72 Linux
  computer with 2 GB of RAM. The FM-1 is a 240 MHz custom-ISA microcontroller
  with 578 KB of SRAM and no Rust or LLVM target. Movy's 8-knob parameter-page
  UI maps almost one-to-one onto the FM-1's 8 knobs, and its Move-style
  sequencer model is a good specification for a C reimplementation.

## Recommended path

1. **Bench characterization, read-only** ([docs/09](docs/09-first-session-checklist.md)).
2. **Prove recovery before anything else** ([docs/07](docs/07-recovery-and-risk.md)):
   get the chip into its mask-ROM USB boot mode through the USB-C port with the
   `USB_KEY` signal, dump the flash, restore it, repeat. Everything else waits
   on this.
3. **First custom code through the mask-ROM route**: the vendor SDK's
   `demo_hello` for AC791N, adapted to the FM-1 board.
4. **The synth**: port msfa / Synth_Dexed, USB-MIDI class device, DX7 SysEx,
   presets in flash.
5. **UI and sequencer** inspired by Movy ([docs/06](docs/06-movy-and-schwung.md)).
6. **Solve the OTA verifier gate** so users can install without opening the case.

## Repository map

| Path | What it is |
| --- | --- |
| [`docs/01-hardware.md`](docs/01-hardware.md) | SoC, memory, board, connectors, what is still unknown |
| [`docs/02-stock-firmware.md`](docs/02-stock-firmware.md) | Package format, boot chain, what the stock app is made of, the msfa finding |
| [`docs/03-update-protocol.md`](docs/03-update-protocol.md) | The SysEx update protocol and the verifier gate that blocks custom packages |
| [`docs/04-prior-art.md`](docs/04-prior-art.md) | Every project, SDK, tool and thread this work stands on |
| [`docs/05-open-source-feasibility.md`](docs/05-open-source-feasibility.md) | What "open firmware" can mean here, the blockers, the verdict |
| [`docs/06-movy-and-schwung.md`](docs/06-movy-and-schwung.md) | Why Movy cannot be ported and what to take from it anyway |
| [`docs/07-recovery-and-risk.md`](docs/07-recovery-and-risk.md) | Recovery paths, risk register, rules of engagement |
| [`docs/08-roadmap.md`](docs/08-roadmap.md) | Phased plan with exit criteria |
| [`docs/09-first-session-checklist.md`](docs/09-first-session-checklist.md) | Exact commands for the first hands-on session |
| [`tools/check_msfa_table.py`](tools/check_msfa_table.py) | Finds the msfa algorithm table in an `app.bin` (tested on V13 and V14) |
| [`tools/fm1_identify.sh`](tools/fm1_identify.sh) | Read-only SysEx identity query via ALSA `amidi` (untested on hardware) |
| [`notes/2026-09-06-research-log.md`](notes/2026-09-06-research-log.md) | What was checked, what was blocked, where the numbers come from |

Confidence marks used throughout the docs: **[verified]** checked in this
project against binaries, photos or SDK files; **[reported]** taken from a
named source and not independently re-checked; **[inferred]** our reading of
the evidence.

## Repository history

The research phase was produced in a Claude Code cloud session that could not
create GitHub repositories (the integration returned `403`), so its first
commit briefly lived on an orphan branch of `ip2k/busybar-dual-timer`. On
2026-09-06 that branch was cloned into `~/Developer/mvave-fm1-firmware` as this
repository's `main`, published as `ip2k/mvave-fm1-open-firmware`. The stray
branch can then be deleted:

```bash
git push https://github.com/ip2k/busybar-dual-timer --delete claude/mvave-fm1-open-firmware-ly2w6u
```

## Credits

This is a synthesis of other people's work, credited in
[`docs/04-prior-art.md`](docs/04-prior-art.md). In particular: **aroum**
(updater analysis, teardown photos), **AL-255** (firmware disassembly, protocol
captures, safety analysis, experimental firmware; WTFPL), **kagaimiq** (JieLi
documentation and tools), **probonopd** (SMK-37 Pro notes), Google's
music-synthesizer-for-android and the Dexed / Synth_Dexed / MiniDexed lineage,
and **charlesvestal** and **DimaDake** for Schwung and Movy. Vendor firmware
images are not redistributed here; see the sources.

## License

MIT for the contents of this repository. Third-party material keeps its own
license as noted where it is referenced.
