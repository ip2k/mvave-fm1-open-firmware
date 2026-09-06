# 01 — Hardware

What the FM-1 is made of, what the stock firmware actually uses, and what still
has to be measured on the bench. Confidence marks: **[verified]** checked in
this project (photos, binaries, SDK files), **[reported]** from a named source,
**[inferred]** our reading.

## 1. The SoC

| Item | Value | Confidence |
| --- | --- | --- |
| Part | JieLi **AC791N**, family codename **WL82** | [verified] product ID string `AC791N_STORY` and `AC791N-v0.01-cfg_tool-v0.10` in the update package (AL-255); SPL byte-identical to the AC79 SDK's `cpu/wl82/tools/uboot.boot` (AL-255) |
| Marking | `C156211-11B8` under the slanted "JL" logo | [verified] visible in aroum's `photo_01.png`; JieLi markings never carry the real part number ([kagaimiq, chip-marks](https://github.com/kagaimiq/jielie/blob/main/chips/chip-marks.md)) |
| Package | LQFP48, leads exposed | [reported] AL-255 `01-hardware-map.md`; photo is consistent (gull-wing leads, not a QFN). The sibling SMK-37 Pro keyboard was identified as AC7911BA in QFN48 by its community |
| CPU | JieLi **pi32v2**: 32-bit, little-endian, Blackfin-derived custom ISA, 16 GPRs, 16/32/48-bit instruction words, algebraic assembly, ELF machine `0xF1` | [reported] kagaimiq `cpu/pi32v2.md`, AL-255 `04-toolchain-and-vendoring.md` |
| Cores | Two "DSP" cores in the family; **stock build uses one** (`CPU_CORE_NUM 1`) | [verified] string `SYSTEM-*modified #define CPU_CORE_NUM 1 *-…-@20220920` in V13 `app.bin`; family spec from the AC79 SDK README |
| Clock | Family max 320 MHz; stock app runs at **240 MHz** from a 24 MHz crystal | [reported] AL-255 `architecture.md`; SDK README for the family max |
| FPU / accel | Single-precision FPU, hardware FFT/matrix, AES-128/256, SHA, CRC16, RNG | [verified] AC79 SDK README |
| SRAM | **578 KB** on chip | [verified] AC79 SDK README (`片上集成了共578K字节SRAM`) |
| SDRAM | Some AC79 packages carry 2 or 8 MB SDRAM; **the FM-1 has none** | [verified] `SDRAM_SIZE = 0` in the FM-1's `isd_config.ini`; LQFP48 packages are the SDRAM-less ones [inferred] |
| Radios | Wi-Fi 802.11 b/g/n and dual-mode Bluetooth 5.0 (BR/EDR + BLE) on chip; Wi-Fi unused by the FM-1, Classic BT vestigial, BLE used for BLE-MIDI | [reported] AL-255 `10-bluetooth.md`; SDK README |
| Peripherals | USB 1.1/2.0 device/host, audio DAC/ADC, I2S, SPI, I2C, UART, SDIO, PWM, timers, ADC, cap-touch, RTC | [verified] SDK README and `include_lib/driver/cpu/wl82/asm/*.h` |
| Register map | Public in the SDK: `include_lib/driver/cpu/wl82/asm/WL82.h` (1330 lines, `JL_*` typedefs; SFR windows `lsfr 0x10000`, `bsfr 0x20000`, `hsfr 0x40000`, `psfr 0x50000`) | [verified] |

The AC79 SDK ships datasheets for the AC7911B, AC7913A0/A6, AC7915A and AC7916A
variants under `doc/datasheet/AC791N规格书/` (Chinese). The FM-1's exact
variant is unknown; the LQFP48 marking points at the AC7911 class. Pinout work
should start from `AC7911B_Datasheet_V1.1.pdf` (1.8 MB) in the SDK mirror.

## 2. Memory and flash

### Address space seen by the stock application [reported: AL-255]

| Range | Contents |
| --- | --- |
| `0x02000000 – 0x0208E59C` | Flash, execute-in-place: `app.bin` (`.text`, `.rodata`, `.data` image) |
| `0x02084820` | `.data` initializer image, copied to RAM at boot |
| `0x01C00000 – 0x01C09E7B` | RAM `.data` (0x9E7C bytes) |
| `0x01C09E7C – 0x01C211FB` | RAM `.bss` (0x17380 bytes) |
| `0x01C14BB4` / `0x01C15BB4` | main / system stack tops (cpu0) |
| `0x01C7FD50` | boot hardware-info struct written from SPL parameters |
| `0x01C7FE00` | RAM interrupt vector table |
| `0x04000120` | cache-locked overlay window (unused in this build, length 0) |
| `0x0001xxxx – 0x0005xxxx` | peripheral SFRs; `0x01EExxxx` interrupt controller |
| `0xFFC0xxxx` | mask-ROM service routines (delay, config write, reset, P33 access) |

Static RAM use of the stock app is therefore about 135 KB plus heap and the
two 11.5 KB display strip buffers; against 578 KB of SRAM that leaves a lot of
headroom for more voices, effects or a sequencer.

### Flash layout (1 MB) [reported: AL-255 `architecture.md`, from the JLFS directory in `FM-1.fwsc`]

| Flash offset | Contents |
| --- | --- |
| `0x00000` | flash header (burner, VID/PID `AC791N`) |
| `0x000A0` | SPL `uboot.boot` ("UBOOT2.00", 14384 bytes) |
| `0x038D0` | `isd_config.ini` (699 bytes; chip key `0x980F`) |
| `0x04000` | app area (JLFS, chip-key encrypted): directory, `app.bin` at `0x4120` (583068 bytes in V13), `cfg_tool.bin` at `0x926BC` (383 bytes), `cfg` at `0x9283B` |
| `0x94000` | VM region: key/value config store, 0x55000 bytes (holds BT MAC, wheel calibration, settings) |
| `0xE9000` | BTIF region (0x1000) |
| `0xEA000` | USR region: user patch storage (0x12000) |
| `0xFC000+` | free; `key_mac` at `0xFF000` |

**V15 moves the boundary [verified, `notes/2026-09-06-bench.md`]:** app area
`0x4000–0x93000`, `cfg_tool.bin` at `0x920DC`, VM at `0x93000` (0x56000 bytes);
`BTIF`, `USR` and the SPL/config region are unchanged.

aroum's README assumes a 4 or 8 MB flash. The package directory and the
SMK-37 Pro notes both point at **1 MB**. No discrete SPI flash chip is visible
in the photos, so the flash is most likely in-package **[inferred]**. Reading
the JEDEC ID from mask-ROM USB mode will settle it (see docs/07).

## 3. The board

Source: aroum's teardown photos (`photos/photo_01..05.png` in
[aroum/fm1-custom-fw](https://github.com/aroum/fm1-custom-fw/tree/main/photos))
plus AL-255's disassembly. Photos are not copied here; they carry no license.

| Item | Observation | Confidence |
| --- | --- | --- |
| Mainboard | Silkscreen `DX7 MB V07 260620` (2026-06-20); bottom marking `MA 26 06 24` | [verified] photos 2, 3, 4 |
| Case | 6 self-tapping screws underneath, one hidden under the centre sticker; rubber feet stay on; plastic latches along the seam | [reported] aroum README §1.3 |
| USB-C | `J6`, top edge, data to the SoC's USB PHY; composite USB-MIDI + UAC1 audio device | [verified] photo 1; enumeration [reported] AL-255 |
| Jacks | two 3.5 mm TRS (`J7`, `J9`) on the top edge: stereo audio out and MIDI IN (TRS) | [verified] photo 1/4; function [reported] product listings and manual |
| Power switch | slide switch at top right | [verified] photo 3/5 |
| Battery | Li-Po `DTP704060`, 3.7 V 2000 mAh 7.4 Wh, dated 2026-06-24, 3-wire connector `电池` (+, −, NTC) | [verified] photo 4 |
| Speaker | 2-pin connector `J11` labelled `喇叭` (speaker), driven by an amplifier stage near two 16 V/100 µF electrolytics | [verified] photo 4; amp part unidentified |
| Display | 1.54" TFT, **240×240 RGB565 over SPI1** (SFR base `0x11D00`), 12–14 pin FPC `J12`; command set `2A/2B/2C/29` (ST7789/ILI9341 class); flushed in ten 240×24 strips | [reported] AL-255 `08-display.md`; FPC [verified] photo 1; 1.54" [reported] user manual via search snippet |
| Knobs | **8 rotary controls**: four in a 2×2 block top right (`E3`, `E6`, …) and four in a column on the right. At least one (top-left of the block, near `RW1`) has a position mark and is probably a potentiometer. The stock firmware polls **two quadrature encoders** and reads **ADC channels 3 and 4** | photos [verified]; encoder/ADC counts [reported] AL-255 `07-input.md`. **The split between encoders and pots is unresolved** — see §6 |
| Keys | 27 silicone keys on interdigitated contact pads, each with an LED | [verified] photos 3/5 |
| Buttons | ~14 tactile switches with LEDs (`K30…K41`, `LED31…LED56`) | [verified] photos 2/3 |
| LED drivers | `U2`, `U3`: two SOIC-20 shift registers (marking reads like `74HC595`) | [verified] photo 1, marking partially legible |
| Key/button scan | GPIO matrix scan (41 inputs) with debounce, plus per-bank locks | [reported] AL-255 `07-input.md` |
| Crystal | 24 MHz (`24.0…` can next to the SoC) | [verified] photo 1; value [reported] AL-255 |
| Antenna | a bare **wire** soldered to pad `P1`, labelled `天线` (antenna) | [verified] photo 1 |
| Passives | `L2 100` buck inductor for the SoC, `L1 4R7`, ferrites `FB1..FB6` on audio | [verified] photo 1 |
| Unidentified | `U9`, `U5` (SOIC-8, near the jacks — audio amp / op-amp candidates), `U11` (SOT-23-6), white 4-pin `OCIC P2362 2619` near the jacks, `Q2`, `Q4`, `D1..D57` | [verified] present; function unknown |
| Debug access | **none**: no JTAG/UART header, no test pads, no recovery button | [reported] aroum README §1.2; photos consistent |
| Reset | `RESET=PB01_08_0`: hold PB01 low for 8 s to reset (long-press power path). **Not** a recovery input | [reported] AL-255 decode of `isd_config.ini` |

## 4. Interfaces as the stock firmware exposes them [reported: AL-255 `06-usb.md`, `05-midi.md`, `11-ota-protocol.md`]

| Interface | Details |
| --- | --- |
| USB, normal mode | VID:PID `4C4A:C755` ("LJ" = JieLi), strings "FM-1 Midi" / "FM-1 Audio" / "Jieli Technology"; USB-MIDI on a 64-byte bulk endpoint pair (EP4) and a UAC1 24-bit stereo isochronous audio interface; serial = chip ID hex. **[verified on the owner's unit 2026-09-06]** USB 2.0 full-speed, `bcdDevice 1.00`, device-level product string `FM-1`, serial `4150353835313708`, five interfaces (0 audio control, 1–2 audio streaming = 2 out / 2 in at 44.1 kHz, 3 audio control, 4 MIDI streaming); CoreMIDI port `FM-1`, CoreAudio device `FM-1 Audio` |
| USB, OTA mode | VID:PID `4D4A:4155` ("ota-FM-1"), same MIDI port name; the OTA loader runs from RAM at `0x01C0A800` |
| UART MIDI | DIN over TRS on the UART at SFR `0x12100`, RX DMA, MIDI-thru merge to TX |
| BLE-MIDI | GATT service, notifications on ATT handle `0x72`; Classic BT profiles (A2DP/AVRCP/HFP) linked but vestigial |
| Audio | internal DAC via DMA ring, 44.1 kHz, 64-sample blocks; digital volume and analog trim calibration in firmware |
| ADC | SARADC channels 3/4 for "wheels" (pitch/mod in the SDK sense) and a battery divider possibly muxed on channel 3 via GPIO 149 |
| Storage | NOR flash over SPI0 (`0x11C00`) with SFC command mode (`0x40200`); FatFS-derived filesystem; ping-pong VM key/value store; DX7 banks as files under `/mnt/sdfile/app/usr` |

## 5. What the SoC gives an open firmware

- Plenty of compute headroom: the stock app renders 12 msfa voices on one core
  at 240 MHz with a third of the clock unused and a whole second core idle.
- 578 KB SRAM against ~135 KB static use.
- A colour TFT with a fast SPI path and an existing strip-buffer rendering
  model that a custom UI can copy.
- Class-compliant USB-MIDI plus USB audio already proven on this silicon.
- A public register map (`WL82.h`) for blob-free drivers, and Apache-2.0 SDK
  sources for reference.

## 6. Open questions for the bench

1. **Knobs**: which of the 8 are encoders and which are potentiometers? Count
   pins and look for detents; the stock firmware's two encoders + two ADC
   channels do not add up to eight, so some knobs may be scanned as matrix
   switches or via the two 74HC595s' neighbours.
2. **Flash**: in-package or discrete? JEDEC ID and size from mask-ROM USB mode.
3. **Exact AC791N variant** and therefore pinout: match the LQFP48 pins to the
   AC7911B datasheet; locate USB D+/D−, the UART candidates (`PB00`, `PB05`,
   `PA05` per SDK comments) and the debug-TAP options (`PA9/PA10`, `PB1/PB2`,
   `PB6/PB7`, or on the USB pins per `sdtap` in the SDK's `isd_config.ini`).
4. **Display FPC pinout** and panel controller ID (`RDDID` `0x04` over SPI).
5. **Audio amp** and codec routing (`U5`, `U9`).
6. **Charger** IC and whether the SoC boots when USB power is applied with the
   power switch off (matters for the `USB_KEY` recovery attempt).
7. **U2/U3** confirm `74HC595`, and how key LEDs are addressed.
