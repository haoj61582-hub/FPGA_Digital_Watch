import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


async def tick(dut):
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


async def tick_n(dut, n):
    if n <= 0:
        return
    await ClockCycles(dut.clk, n)
    await Timer(1, unit="ns")


@cocotb.test()
async def test_brightness_timepiece_smoke(dut):
    """
    Integration test for user_top_brightness_timepiece.

    Section 1: mode switching works  -- proves user_top_timepiece_v1 is
    instantiated (not user_top or any other wrong module).

    Section 2: PWM brightness blanking  -- all four brightness levels are
    exercised, and all three blank outputs (hours, minutes, seconds) are
    verified to agree on every cycle.

    Section 3: app blanking passthrough at full brightness  -- the wrapper
    ORs blanking_pwm with the app's own blank signals.  At full brightness
    (blanking_pwm=0) the app's signals must still reach the outputs.  The
    watch is put into seconds edit mode; blank_seconds must pulse high while
    blank_hours and blank_minutes must stay 0 throughout.
    """
    CPS = int(dut.CYCLES_PER_SECOND.value)
    CPms = CPS // 1000  # PWM counter period in clock cycles

    dut.button.value = 0
    await Timer(1, unit="ns")
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.sw.value = 0b10 << 8  # full brightness, watch mode
    await tick(dut)

    # -----------------------------------------------------------------------
    # Section 1: the inner module is user_top_timepiece_v1, not user_top
    # -----------------------------------------------------------------------

    # Watch auto-counts; after CPS cycles seconds_disp must be 1.
    cocotb.log.info(f"Section 1: watch mode  -- wait {CPS} cycles, expect seconds=1")
    await tick_n(dut, CPS)
    assert int(dut.seconds_disp.value) == 1, (
        f"Expected seconds=1 after {CPS} cycles in watch mode, "
        f"got {int(dut.seconds_disp.value)}  -- is user_top_timepiece_v1 instantiated?"
    )

    # Stopwatch has not been started, so switching to it must show seconds=0.
    # user_top has no mode mux and would fail here.
    cocotb.log.info("Section 1: switch to stopwatch (sw[1:0]=01)  -- expect seconds=0")
    dut.sw.value = (0b10 << 8) | 0b01  # full brightness, stopwatch mode
    await tick(dut)
    assert int(dut.seconds_disp.value) == 0, (
        f"Expected seconds=0 in stopwatch mode (not started), "
        f"got {int(dut.seconds_disp.value)}  -- wrong module instantiated?"
    )

    # -----------------------------------------------------------------------
    # Section 2: PWM brightness blanking is wired correctly
    # -----------------------------------------------------------------------

    # In normal watch mode the app asserts no blanking of its own
    # (orig_blank_x = 0), so all three outputs equal blanking_pwm directly.
    # For each non-full brightness level: all three blank outputs must go high
    # within two PWM periods and must always agree with each other.
    # For full brightness: all three must stay 0 for two PWM periods.

    for code, label in [(0b11, "50%"), (0b01, "25%"), (0b00, "12.5%")]:
        cocotb.log.info(
            f"Section 2: {label} brightness (sw[9:8]={code:02b})  -- "
            f"all blank outputs must go high within {CPms * 2} cycles"
        )
        dut.sw.value = (code << 8) | 0b00  # brightness + watch mode
        await tick(dut)
        seen_high = False
        for cyc in range(CPms * 2):
            await tick(dut)
            bh = int(dut.blank_hours.value)
            bm = int(dut.blank_minutes.value)
            bs = int(dut.blank_seconds.value)
            assert bh == bm == bs, (
                f"{label}: blank outputs disagree at cycle {cyc}  -- "
                f"hours={bh} minutes={bm} seconds={bs}"
            )
            if bh:
                seen_high = True
                break
        assert seen_high, (
            f"blank outputs never went high within {CPms * 2} cycles "
            f"at {label} brightness  -- PWM blanking not applied"
        )
        cocotb.log.info(f"Section 2: {label} blanking confirmed")

    cocotb.log.info(
        f"Section 2: full brightness (sw[9:8]=10)  -- "
        f"all blank outputs must stay 0 for {CPms * 2} cycles"
    )
    dut.sw.value = (0b10 << 8) | 0b00  # full brightness, watch mode
    await tick(dut)
    for cyc in range(CPms * 2):
        await tick(dut)
        assert int(dut.blank_hours.value) == 0, (
            f"blank_hours high at cycle {cyc} at full brightness"
        )
        assert int(dut.blank_minutes.value) == 0, (
            f"blank_minutes high at cycle {cyc} at full brightness"
        )
        assert int(dut.blank_seconds.value) == 0, (
            f"blank_seconds high at cycle {cyc} at full brightness"
        )
    cocotb.log.info("Section 2: full brightness confirmed")

    # -----------------------------------------------------------------------
    # Section 3: app blanking passes through the OR gate at full brightness
    # -----------------------------------------------------------------------

    # Hold button[3] for CPS+1 cycles to trigger the watch edit-mode selector.
    # The watch enters seconds edit mode (mode_enable = 0b001), which makes the
    # watch's own pwm_out pulse orig_blank_seconds high.
    # With blanking_pwm=0 (full brightness):
    #   blank_seconds = orig_blank_seconds | 0  -- must go high when watch PWM is high
    #   blank_hours   = orig_blank_hours   | 0  -- must stay 0 (not in hours edit)
    #   blank_minutes = orig_blank_minutes | 0  -- must stay 0 (not in minutes edit)
    # Sample for one full watch PWM period (CPS // 2 + 1 cycles) to guarantee
    # catching the high phase (watch PWM duty cycle = CPS // 10 out of CPS // 2).
    cocotb.log.info("Section 3: full brightness, hold button[3] to enter watch seconds edit mode")
    dut.sw.value = (0b10 << 8) | 0b00  # full brightness, watch mode
    dut.button.value = 0b1000  # hold button[3]
    await tick_n(dut, CPS + 1)
    dut.button.value = 0

    watch_pwm_period = CPS // 2 + 1
    seen_blank_seconds = False
    cocotb.log.info(
        f"Section 3: sampling {watch_pwm_period} cycles  -- "
        "blank_seconds must pulse high, blank_hours/minutes must stay 0"
    )
    for _ in range(watch_pwm_period):
        await tick(dut)
        if int(dut.blank_seconds.value):
            seen_blank_seconds = True
        assert int(dut.blank_hours.value) == 0, (
            "blank_hours went high  -- should be 0 at full brightness "
            "when only seconds edit mode is active"
        )
        assert int(dut.blank_minutes.value) == 0, (
            "blank_minutes went high  -- should be 0 at full brightness "
            "when only seconds edit mode is active"
        )
    assert seen_blank_seconds, (
        "blank_seconds never went high during watch seconds edit mode at full brightness  -- "
        "app blanking does not pass through the OR gate"
    )
    cocotb.log.info("Section 3: app blanking passthrough confirmed")
