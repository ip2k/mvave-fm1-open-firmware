#!/usr/bin/env bash
# Read-only identity query for an M-VAVE FM-1 over ALSA raw MIDI (Linux).
#
# Sends the ten-byte query the official updater uses and prints the reply.
# Nothing else is sent. UNTESTED ON HARDWARE as of 2026-09-06; the byte
# sequences come from aroum/fm1-custom-fw and AL-255/FM-1-RE, which captured
# them from the official updater.
#
# Expected reply (41 bytes): F0 00 32 45 58 01 00 00 23 4D 5A 44 ... 40 05 F7
#   - model name is the ASCII before '_', a 20-byte field encodes the version
#     (ASCII '0' added to each byte), the decimal suffix is the firmware version.
#
# Raw MIDI is unavailable while PipeWire/JACK/aseq clients hold the port. If
# amidi reports "Device or resource busy", stop them for the session or use
# AL-255's sequencer-based client:  python3 FM-1-RE/tools/fm1_ota.py scan
#
# Usage: tools/fm1_identify.sh [hw:X,0,0]
set -euo pipefail

QUERY='F0 00 32 45 00 00 00 40 7F F7'

if ! command -v amidi >/dev/null; then
  echo "amidi not found (install alsa-utils)"; exit 1
fi

PORT="${1:-}"
if [ -z "$PORT" ]; then
  PORT=$(amidi -l | awk 'tolower($0) ~ /fm-1/ {print $2; exit}')
fi
if [ -z "$PORT" ]; then
  echo "No FM-1 MIDI port found. Ports:"; amidi -l; exit 1
fi

echo "port: $PORT"
echo "sending: $QUERY"
# -S sends the hex bytes, -d dumps incoming bytes, -t stops after N seconds of silence.
amidi -p "$PORT" -S "$QUERY" -d -t 3
