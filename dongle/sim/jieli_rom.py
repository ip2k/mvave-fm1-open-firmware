"""Behavioural model of the JieLi mask ROM's USB_KEY entry, from kagaimiq's
write-ups (jielie/isp/usb/usb-key.md, jl-uboot-tool/docs/how-to-enter-uboot.md).
Everything here is [reported] behaviour of other JieLi families; nothing has
been observed on an AC791N yet. Levels are resolved bus levels (0/1)."""

USB_KEY = 0x16EF


class JieLiMaskRom:
    def __init__(self, clock_line="dp", ack_us=1500, listen_window_us=None,
                 sof_window_us=1_000_000, sof_attempts=None, sof_periods_needed=4,
                 sof_tolerance=0.02, retry_gap_us=2000, usb_init_us=5000, powered=True,
                 first_window_us=None):
        assert clock_line in ("dp", "dm")
        self.clock_line = clock_line
        self.ack_us = ack_us
        self.listen_window_us = listen_window_us
        self.sof_window_us = sof_window_us
        self.first_window_us = first_window_us     # models a first window that started before our pulses
        self.sof_attempts = sof_attempts
        self.sof_periods_needed = sof_periods_needed
        self.sof_tolerance = sof_tolerance
        self.retry_gap_us = retry_gap_us
        self.usb_init_us = usb_init_us
        self.powered = powered
        self.state = "listen" if powered else "off"
        self.shift = 0
        self.nbits = 0
        self.prev_clock = None
        self.prev_dp = None
        self.ack_at = None
        self.dp_pullup = False
        self.falling = []
        self.sof_started = None
        self.attempt = 0
        self.measured_period_us = None
        self.calibrated_at = None
        self.log = []

    # ---- electrical outputs -------------------------------------------------
    def drives_low(self):
        """(dp_low, dm_low): the chip only drives during the acknowledge."""
        low = self.state == "ack"
        return low, low

    def pulls_up_dp(self):
        return self.dp_pullup

    # ---- behaviour --------------------------------------------------------------
    def step(self, t_us, dp, dm):
        if self.state == "listen":
            if self.listen_window_us is not None and t_us > self.listen_window_us:
                self.state = "boot_flash"
                self.log.append(("boot_flash", t_us))
                return
            clk = dp if self.clock_line == "dp" else dm
            dat = dm if self.clock_line == "dp" else dp
            if self.prev_clock == 0 and clk == 1:            # data latched on the rising edge
                self.shift = ((self.shift << 1) | dat) & 0xFFFF
                self.nbits += 1
                if self.nbits >= 16 and self.shift == USB_KEY:
                    self.state = "ack"
                    self.ack_at = t_us
                    self.log.append(("ack", t_us))
            self.prev_clock = clk
        elif self.state == "ack":
            if t_us >= self.ack_at + self.ack_us:
                self._start_sof_attempt(t_us)
        elif self.state == "sof_wait":
            if self.prev_dp == 1 and dp == 0:
                self.falling.append(t_us)
                if len(self.falling) > self.sof_periods_needed:
                    recent = self.falling[-(self.sof_periods_needed + 1):]
                    periods = [b - a for a, b in zip(recent, recent[1:])]
                    mean = sum(periods) / len(periods)
                    if all(abs(p - mean) <= self.sof_tolerance * mean for p in periods):
                        self.measured_period_us = mean
                        self.state = "calibrated"
                        self.dp_pullup = False
                        self.calibrated_at = t_us
                        self.log.append(("calibrated", t_us, mean))
            window = self.first_window_us if (self.attempt == 1 and self.first_window_us) else self.sof_window_us
            if self.state == "sof_wait" and t_us - self.sof_started > window:
                self.dp_pullup = False
                self.state = "sof_retry_gap"
                self.retry_at = t_us + self.retry_gap_us
                self.log.append(("sof_retry", t_us))
            self.prev_dp = dp
        elif self.state == "sof_retry_gap":
            if t_us >= self.retry_at:
                if self.sof_attempts is not None and self.attempt >= self.sof_attempts:
                    self.state = "boot_flash"
                    self.log.append(("boot_flash", t_us))
                else:
                    self._start_sof_attempt(t_us)
        elif self.state == "calibrated":
            if t_us >= self.calibrated_at + self.usb_init_us:
                self.state = "usb_ready"          # enumerates as UBOOT1.00 mass storage
                self.dp_pullup = True
                self.log.append(("usb_ready", t_us))

    def _start_sof_attempt(self, t_us):
        self.attempt += 1
        self.state = "sof_wait"
        self.dp_pullup = True
        self.sof_started = t_us
        self.falling = []
        self.prev_dp = None
