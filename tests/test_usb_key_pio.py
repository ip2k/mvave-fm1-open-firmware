"""The PIO programs, run in rp2040-pio-emulator, must produce the JieLi key
waveform and the 1 ms SOF pulse train exactly as docs/10 specifies."""
from dongle.sim import pio_waveform
from dongle.sim.params import PARAMS


def rising_edge_samples(wave):
    """Decode the packet like the ROM does: sample data at each clock rising edge."""
    bits, edges = [], []
    prev_clock_level = 1
    for t, (clock_low, data_low) in enumerate(wave):
        clock_level = 0 if clock_low else 1
        if prev_clock_level == 0 and clock_level == 1:
            bits.append(0 if data_low else 1)
            edges.append(t)
        prev_clock_level = clock_level
    return bits, edges


def test_key_packet_bits_and_timing():
    wave = pio_waveform.key_packet_waveform(PARAMS["USB_KEY_WORD"])
    bits, edges = rising_edge_samples(wave)
    assert len(bits) == 16
    value = int("".join(str(b) for b in bits), 2)
    assert value == PARAMS["USB_KEY_WORD"] == 0x16EF
    periods = [b - a for a, b in zip(edges, edges[1:])]
    assert periods == [PARAMS["KEY_BIT_CYCLES"]] * 15
    # data must be stable for at least 4 cycles before every rising edge
    for e in edges:
        assert len({wave[t][1] for t in range(e - 4, e + 1)}) == 1
    # both lines released at the end of the packet
    assert wave[-1] == (False, False)
    assert len(wave) <= PARAMS["KEY_PACKET_US"]


def test_key_packet_never_drives_between_words():
    wave = pio_waveform.key_packet_waveform(0x0000)   # all-zero key: data driven low the whole time
    bits, _ = rising_edge_samples(wave)
    assert bits == [0] * 16
    wave = pio_waveform.key_packet_waveform(0xFFFF)   # all-one key: data never driven
    assert not any(data_low for _, data_low in wave)


def test_sof_pulse_period_and_width():
    wave = pio_waveform.sof_waveform(periods=3)
    lows = [t for t, (low,) in enumerate(wave) if low]
    # three pulses of SOF_PULSE_CYCLES, SOF_PERIOD_CYCLES apart
    starts = [t for t in lows if t == 0 or not wave[t - 1][0]]
    assert len(starts) == 3
    assert [b - a for a, b in zip(starts, starts[1:])] == [PARAMS["SOF_PERIOD_CYCLES"]] * 2
    for s in starts:
        assert all(wave[s + i][0] for i in range(PARAMS["SOF_PULSE_CYCLES"]))
        assert not wave[s + PARAMS["SOF_PULSE_CYCLES"]][0]
