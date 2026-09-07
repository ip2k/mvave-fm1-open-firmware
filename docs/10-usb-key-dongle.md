# 10 — The `USB_KEY` recovery dongle (RP2040)

Specification, reference implementation and test harness for the dongle that
puts the FM-1's JieLi AC791N into its mask-ROM USB download mode
(`UBOOT1.00`) through the USB-C port, so the flash can be dumped and restored
without opening the case. This is Phase 2 of the roadmap (docs/08): nothing
else may be written to the device until this works (docs/07 §4).

Status 2026-09-06: **specified, implemented and simulated; not yet run against
an FM-1.** Confidence marks as elsewhere: [reported] = kagaimiq's write-ups,
[inferred] = our reading, [verified] = checked in this repository (host-side
simulation counts as verification of the *logic*, not of the chip's response).

## 1. What the mask ROM does [reported: kagaimiq]

Sources: `jielie/isp/usb/usb-key.md` and
`jl-uboot-tool/docs/how-to-enter-uboot.md` (both by kagaimiq, cloned under
`reference/`). Their content, condensed:

1. At power-up the boot ROM watches the USB data lines for a **16-bit key
   `0x16EF`** (`0001 0110 1110 1111`), sent **MSB first**, one line as clock
   and the other as data; the ROM latches data on the **rising edge** of the
   clock. Reception is software with a timer capture, so the clock "should not
   be too fast"; the vendor dongle uses about **50 kHz**.
2. The key is repeated until the chip acknowledges by **pulling both D+ and
   D− low for about 1–2 ms**. From then on the ROM stops listening for the
   key and initialises USB.
3. **The two write-ups disagree on the pin roles.** `usb-key.md` (with scope
   captures): D+ = clock, D− = data. `how-to-enter-uboot.md` (ASCII diagram):
   D− = clock, D+ = data. The dongle therefore supports both and can alternate.
4. Sensing the acknowledge needs a **strong external pull-up (< 4.7 kΩ)** on
   each line: the chip keeps its 15 kΩ USB pull-downs active while receiving
   the key, and if the PC is also attached the pull-down becomes 7.5 kΩ, which
   defeats MCU-internal pull-ups and produces false acknowledges.
5. After the acknowledge the chip **pulls D+ up (1.5 kΩ) and measures the
   interval between falling edges on D+** to calibrate its PLL from the host's
   1 ms SOF cadence. It needs about four consistent periods; if nothing arrives
   within roughly a second it drops the pull-up and tries again (forever on
   older families, three times on newer ones — unknown for WL82). Any other
   full/low-speed traffic on the same bus segment can confuse the measurement;
   an isolated port (xHCI ports are isolated by design) or a dedicated USB 2.0
   hub avoids that.
6. Alternatively the **dongle itself can supply the "SOF" edges**: after the
   acknowledge, wait for D+ to go high, drive a short negative pulse every
   1.000 ms until D+ goes low (calibration done), then connect the PC. The
   chip then works regardless of bus activity.
7. In `UBOOT1.00` the chip enumerates as a **USB mass-storage device** that
   speaks JieLi's SCSI vendor protocol (v2 for WL82). It can only read/write
   RAM and jump; flash access needs the `wl82loader.bin` blob loaded to
   `0x1C02000` (jl-uboot-tool, "MengLi" memory cipher quirk). WL82 is listed
   there as **"unknown"** (loader present, never exercised).

The vendor's own "USB Updater" dongle is exactly this: a small JieLi MCU that
bit-bangs the key and a USB switch that then passes the bus to the PC.

## 2. Requirements

Functional

- R1 Send the key continuously from before the target powers up until the
  acknowledge, in either pin polarity (fixed or alternating in blocks).
- R2 Detect the acknowledge reliably (both lines low ≥ 100 µs while the dongle
  drives nothing) and never while the target is unpowered or absent.
- R3 After the acknowledge, either hand the bus to the PC immediately
  (`SOF_MODE_PC`) or generate 1 ms falling edges on D+ until the chip finishes
  calibration, then hand over (`SOF_MODE_DONGLE`, default).
- R4 Report every step and its timing on a serial console; show state on the
  LED; allow a restart with a button.
- R5 Keep the target's VBUS connected to the PC at all times so the FM-1 sees a
  normal USB power source.

Electrical and safety

- E1 Never drive a line high: **open-drain only** (drive low or release). The
  chip pulls both lines low during the acknowledge, and push-pull outputs
  would short against it.
- E2 3.3 V logic on both sides (USB signalling is 3.3 V); 100 Ω series
  resistors on the two GPIO lines as a fault limiter.
- E3 The pull-ups (2.2 kΩ to 3.3 V) must be switchable, because during the
  SOF phase the dongle has to *see* the chip release its own D+ pull-up, and a
  strong dongle pull-up would mask that (2.2 kΩ against 15 kΩ still reads high).
- E4 With the dongle unpowered the target must be connected straight to the
  PC (relay normally-closed contacts = PC side).
- E5 Nothing here writes to the device. Entering `UBOOT1.00` is a read-only
  event; all flash writes are separate, deliberate `jluboottool` commands
  covered by docs/07 §4.

## 3. Hardware

```
                 ┌──────────────────────────────────────────────────┐
   PC  ══USB══►  │ HOST port (USB-C/micro-B breakout)               │
   (data+5V)     │   VBUS ───────────────────────────────┬── VBUS   │  TARGET port
                 │   D+  ──┐                              │          │  (USB-A female
                 │   D−  ──┼── K1 DPDT relay (NC = PC) ───┼── D+/D− ═╪══ USB-A→C cable ══► FM-1
                 │         │       │ NO = dongle           │          │
                 │         │       │                       │          │
                 │  Pico   │   GP14 ─100Ω─┬── D+ (dongle side)        │
                 │  GP16 ──┴─2.2k──────────┤                          │
                 │  GP16 ────2.2k──┐       │                          │
                 │  GP15 ─100Ω─────┴───────┼── D− (dongle side)       │
                 │  GP17 ── 2N7002 gate → K1 coil (+flyback diode)    │
                 │  GP18 ── button to GND  GP25 ── on-board LED        │
                 │  Pico micro-USB ══► PC (power + serial console)     │
                 └──────────────────────────────────────────────────┘
```

Bill of materials (reference build, all through-hole/breakout friendly)

| Ref | Part | Why |
| --- | --- | --- |
| U1 | Raspberry Pi Pico (RP2040) | PIO gives cycle-exact open-drain bit-banging and a 1.000 ms pulse train; USB CDC console for free |
| J1 | USB-A female breakout (TARGET) | plug the FM-1 in with an ordinary USB-A→C cable; avoids USB-C CC/Rp handling entirely |
| J2 | USB-C or micro-B female breakout (HOST) | the PC's pass-through connection; supplies TARGET VBUS |
| K1 | DPDT signal relay, 3 V or 5 V coil (e.g. Omron G6K-2F-Y / Panasonic TQ2) | transparent switch for a full-speed bus; NC contacts wired to the PC so the default path is "straight through" |
| Q1, D1 | 2N7002 (or any logic-level N-MOSFET), 1N4148 across the coil | coil current exceeds a GPIO's 12 mA |
| R1, R2 | 2.2 kΩ from D+ and D− (dongle side) to GP16 | switchable strong pull-ups (E3, §1 item 4) |
| R3, R4 | 100 Ω in series with GP14 and GP15 | fault current limit, ESD |
| SW1 | tactile button GP18–GND | restart / polarity select |

Alternatives: a TS3USB221 / FSUSB42 USB 2.0 mux instead of K1 (SEL from GP17,
dongle side = "NO"); or, for a first prototype, a **manual DPDT slide switch**
as in the vendor's V2/V3 dongle, flipped when the LED says so (only with
`SOF_MODE_DONGLE`, which makes the hand-over timing non-critical).

Pin map (`dongle/firmware/config.h`)

| GPIO | Name | Direction | Function |
| --- | --- | --- | --- |
| GP14 | `PIN_DP` | open-drain / input | D+ of the target (via 100 Ω) |
| GP15 | `PIN_DM` | open-drain / input | D− of the target (via 100 Ω) |
| GP16 | `PIN_PULLUP_EN` | output-high or hi-Z | top of the two 2.2 kΩ pull-ups |
| GP17 | `PIN_MUX_SEL` | output | 1 = relay energised = dongle owns the bus |
| GP18 | `PIN_BUTTON` | input, internal pull-up | short press: restart; hold at boot: fixed polarity |
| GP25 | LED | output | state indication |

Power: the Pico runs from its own micro-USB (also the console). TARGET VBUS
comes from the HOST port's VBUS straight through (R5). Do not tie the two 5 V
rails together.

## 4. Firmware (`dongle/firmware/`)

Two PIO programs (`usb_key.pio`) and a small state machine in `main.c`.

`usb_key` — bit-bangs one 16-bit key packet per TX-FIFO word. The word holds
the key **inverted** in its top 16 bits so that `out pindirs, 1` writes the
pin *direction* (1 = drive low) straight from the data; the pin's output value
is latched at 0 and never changes, which is the open-drain trick (E1). Timing
at a 1 MHz PIO clock: clock low 8 µs (data changes 3 µs after the falling
edge), clock released 12 µs → 20 µs per bit, 50 kHz, 320 µs per packet. After
the 16 bits both lines are released and the state machine stalls on `pull
block` until the CPU sends the next word; that stall is the inter-packet gap
in which the CPU samples for the acknowledge.

`sof_pulse` — drives D+ low for 4 µs every 1000 µs (cycle-counted, crystal
accurate), used in `SOF_MODE_DONGLE`.

Control flow (`main.c`, mirrored line-for-line by `dongle/sim/dongle.py`):

```
SELFTEST   pull-ups on, lines released → both must read high, else FAULT
KEY        loop: put packet word → wait 326 µs → gap 160 µs sampling both lines
           every 10 µs; both low for ≥ 100 µs ⇒ ACK. Polarity: fixed, or
           alternate every 40 packets (≈ 20 ms per block).
ACK        log polarity and packet count; stop the key; wait ≤ 20 ms for both
           lines to be released again
SOF_MODE_PC:      pull-ups off → relay to PC → DONE
SOF_MODE_DONGLE:  pull-ups off → wait ≤ 500 ms for D+ high (chip pull-up)
                  → start sof_pulse → sample D+ every 100 µs (outside our own
                  4 µs pulses) → 30 consecutive low samples (3 ms) ⇒ chip
                  released D+ ⇒ stop pulses → relay to PC → DONE
                  (6 s overall timeout ⇒ FAILED)
DONE       LED solid; console prints the next command to run on the PC
FAILED/FAULT  LED pattern; button restarts (power-cycle the FM-1 first)
```

Parameters (single source of truth `config.h`; the simulator reads the same
file, and a test fails if the two drift):

| Parameter | Value | Note |
| --- | --- | --- |
| `USB_KEY_WORD` | `0x16EF` | MSB first |
| `KEY_BIT_CYCLES` | 20 (µs) | 50 kHz |
| `KEY_GAP_US` | 160 | packet period ≈ 486 µs |
| `ACK_MIN_LOW_US` | 100 | real ACK is 1000–2000 µs |
| `KEY_PACKETS_PER_POLARITY` | 40 | alternate mode |
| `SOF_PERIOD_CYCLES` / `SOF_PULSE_CYCLES` | 1000 / 4 | 1.000 ms, 4 µs low |
| `SOF_DP_HIGH_TIMEOUT_MS` | 500 | chip should pull D+ up within ms |
| `SOF_DONE_LOW_MS` | 3 | D+ low this long = calibration finished |
| `SOF_PHASE_TIMEOUT_MS` | 6000 | covers several ROM retry windows |

LED: 1 Hz blink = keying; 3 fast blinks = ACK; solid = DONE; 5 Hz = FAILED;
10 Hz = FAULT (self-test). Console (115200 8N1 over the Pico's USB CDC) prints
one line per transition with microsecond timestamps.

## 5. Host side after `UBOOT1.00`

- **Use a Linux PC** (or Windows). `jl-uboot-tool` talks SCSI through
  `/dev/sg*` or `\\.\HardDiskVolumeN`; its device finder has no macOS path.
  Any Linux box on the LAN (or a Raspberry Pi) with the dongle attached works.
- Expected: a new mass-storage device whose SCSI inquiry product string is
  `UBOOT1.00` (vendor-family prefix unknown for WL82; BR23–BR34 use VID
  `4C4A` with PIDs `x342`). `python3 jldevfind.py` lists it.
- Then, **read-only first**: `python3 jluboottool.py --chip wl82` loads
  `wl82loader.bin` (address `0x1C02000`, MengLi cipher); inside the shell,
  identify the flash (JEDEC ID; expect a 1 MB density code `0x14`) and
  `read 0 0x100000 dump1.bin`. Power-cycle, re-enter, `read` again to
  `dump2.bin`; the two must be identical and must match the stock package
  where it maps (docs/01 §2). Only then is a `write` of `dump1.bin` allowed,
  followed by a third dump. Exit criteria are in docs/08 Phase 2.
- `jlrunner.py` can load and run code in RAM without touching flash; that is
  the path for the first custom code (docs/08 Phase 3).

## 6. Bench procedure (first attempt)

1. Build the dongle; before connecting the FM-1, power the Pico and watch the
   console: `SELFTEST ok` means the pull-ups and lines are wired. With a
   scope or logic analyser on D+/D−, confirm the 50 kHz packets and the
   ~160 µs gaps (optional but cheap insurance).
2. Connect the HOST port to the Linux PC and the FM-1 (**switched off**) to
   the TARGET port with a USB-A→C cable. Note whether the FM-1 shows any sign
   of USB power (docs/01 §6 item 6 is still open).
3. Start keying (default: alternating polarity, `SOF_MODE_DONGLE`). Switch the
   FM-1 on. Expected within a second: `ACK polarity=<A|B> packets=<n>`, then
   `D+ high`, `SOF pulses`, `D+ released after <n> pulses`, `bus → PC`, and
   `UBOOT1.00` on the PC.
4. If no ACK: repeat with each fixed polarity (hold the button at boot to
   select), then with the FM-1 already on before keying, then with
   `SOF_MODE_PC`. Record every attempt in `notes/`.
5. If the stock app boots instead (the FM-1's screen comes up, `4C4A:C755`
   appears on the PC after the relay switches), the ROM did not honour the
   key: see §7.
6. First success: record polarity, timing lines, the PC's `lsusb` output and
   the SCSI inquiry string in `notes/`, then follow §5.

## 7. Test harness (`dongle/sim/`, `tests/test_dongle_*.py`)

- `tests/test_usb_key_pio.py` assembles `usb_key.pio` with `adafruit_pioasm`
  and runs it in `rp2040-pio-emulator`: the emitted waveform is decoded by a
  model of the ROM's receiver (rising-edge sampling) and must yield `0x16EF`
  with 20-cycle bit periods and ≥ 4 cycles of data setup; the `sof_pulse`
  program must produce exactly 1000-cycle periods with 4-cycle low pulses.
- `dongle/sim/jieli_rom.py` is a behavioural model of the ROM per §1 (key
  receiver in either polarity, 1.5 ms acknowledge, D+ pull-up and SOF period
  measurement with retry windows, optional short listening window).
- `dongle/sim/dongle.py` is the control logic of `main.c` in Python, driven
  by the *emulated PIO waveforms*, and `dongle/sim/cosim.py` resolves the two
  open-drain parties on a shared bus microsecond by microsecond.
- `tests/test_dongle_model.py` runs the whole sequence end to end for both ROM
  polarities and both SOF modes, checks that the dongle reports the right
  polarity, that no acknowledge is detected with an absent or unpowered
  target, that a wrong fixed polarity never triggers, and that
  `config.h` and the model agree.

What the harness cannot tell us: whether the AC791N's ROM honours the key on
the FM-1's wiring, the real listening window at power-up, the true polarity,
and whether VBUS alone powers the SoC. Those are §6.

## 8. Risks and open questions

| Item | Status |
| --- | --- |
| Pin polarity (which line is clock) | unknown; both implemented |
| Does the ROM listen continuously or only briefly at power-up? | unknown; alternate mode assumes continuous, fixed mode covers the other case |
| Does the FM-1 SoC start on VBUS with the switch off? | unknown (docs/01 §6) |
| Series/ESD parts between the USB-C receptacle and the SoC | unknown; 2.2 kΩ pull-ups tolerate a few hundred ohms in series |
| WL82 `UBOOT1.00` VID:PID and inquiry string | unknown; jl-uboot-tool marks WL82 "unknown" — read-only commands first |
| MengLi cipher / loader block size for wl82 | from `usb-loaders.yaml` [reported] |
| Battery keeps the SoC powered while "off" | if so, the key must be present at the moment the switch is thrown; the dongle keys continuously, so this only matters for how the power-up is sequenced |

## 9. Sources

kagaimiq — `jielie/isp/usb/usb-key.md`, `jielie/isp/index.md`,
`jl-uboot-tool/docs/how-to-enter-uboot.md`, `what-is-uboot.md`,
`usb-protocol.md`, `usb-loader-v2.md`, `data/usb-loaders.yaml`,
`data/chips.yaml`; RP2040 datasheet (PIO, pad electrical characteristics);
USB 2.0 specification §7.1 (pull-up/pull-down values, full-speed signalling).
