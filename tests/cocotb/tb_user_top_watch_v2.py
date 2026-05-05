import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


async def tick(dut):
    """Advance one clock cycle and wait for outputs to settle."""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


async def tick_n(dut, n):
    """Advance n clock cycles."""
    if n <= 0:
        return
    await ClockCycles(dut.clk, n)
    await Timer(1, unit="ns")


async def press(dut, cycles):
    """Hold button[3] high for `cycles` clock cycles then release."""
    dut.button.value = dut.button.value.to_unsigned() | 0b1000
    await tick_n(dut, cycles)
    dut.button.value = dut.button.value.to_unsigned() & ~0b1000
    await tick(dut)


async def measure_pwm(dut, signal, max_cycles):
    """Measure one complete PWM period of signal.

    Finds the next rising edge, then counts the high duration and the
    subsequent low duration.  Returns (high_cycles, low_cycles).
    """
    # Ensure we start from a 0 so we catch a clean rising edge.
    for _ in range(max_cycles):
        await tick(dut)
        if int(signal.value) == 0:
            break
    else:
        assert False, f"Signal never went low within {max_cycles} cycles"

    # Wait for the rising edge (0 -> 1).
    for _ in range(max_cycles):
        await tick(dut)
        if int(signal.value) == 1:
            break
    else:
        assert False, f"Signal never went high within {max_cycles} cycles"

    # Count how many cycles it stays high (including the current cycle).
    high = 1
    for _ in range(max_cycles):
        await tick(dut)
        if int(signal.value) == 0:
            break
        high += 1

    # Count how many cycles it stays low (including the current cycle).
    low = 1
    for _ in range(max_cycles):
        await tick(dut)
        if int(signal.value) == 1:
            break
        low += 1

    return high, low


@cocotb.test()
async def test_mode_selection(dut):
    """Mode selection: long press enters edit mode, short presses cycle fields,
    blank signals flash at the correct rate and duty cycle."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    dut.sw.value = 0
    await tick(dut)

    CPS = int(dut.CYCLES_PER_SECOND.value)
    HOLD   = CPS            # long-press threshold (one simulated second)
    PERIOD = CPS // 2       # PWM period in cycles  (0.5 s -> 2 Hz)
    HIGH   = CPS // 10      # PWM high duration     (0.1 s -> 20% -> 80% on)
    LOW    = PERIOD - HIGH  # PWM low duration      (0.4 s)
    cocotb.log.info(
        f"CPS={CPS}  HOLD={HOLD}  PWM period={PERIOD}  high={HIGH}  low={LOW}"
    )

    # -----------------------------------------------------------------------
    # Section 1: normal mode - all blank signals are 0
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 1: normal mode, blank_* all zero")
    await tick_n(dut, 3)
    assert int(dut.blank_seconds.value) == 0, "blank_seconds must be 0 in normal mode"
    assert int(dut.blank_minutes.value) == 0, "blank_minutes must be 0 in normal mode"
    assert int(dut.blank_hours.value)   == 0, "blank_hours must be 0 in normal mode"

    # -----------------------------------------------------------------------
    # Section 2: one cycle short of threshold does not enter edit mode
    # -----------------------------------------------------------------------
    # button_hold_detect asserts held after exactly HOLD rising edges;
    # HOLD-1 edges leaves count at HOLD-1 and held never fires.
    cocotb.log.info(f"Section 2: press of {HOLD - 1} cycles (HOLD-1) does not enter edit mode")
    await press(dut, HOLD - 1)
    await tick_n(dut, 3)
    assert int(dut.blank_seconds.value) == 0, "blank_seconds must stay 0 for HOLD-1 press"
    assert int(dut.blank_minutes.value) == 0, "blank_minutes must stay 0 for HOLD-1 press"
    assert int(dut.blank_hours.value)   == 0, "blank_hours must stay 0 for HOLD-1 press"

    # -----------------------------------------------------------------------
    # Section 3: exactly HOLD cycles enters edit mode - seconds field selected
    # -----------------------------------------------------------------------
    # After HOLD rising edges held goes high; the release tick fires the
    # pulse and arms the latch - the minimum press that enters edit mode.
    cocotb.log.info(f"Section 3: press of exactly {HOLD} cycles enters edit mode, seconds selected")
    await press(dut, HOLD)
    await tick_n(dut, 3)
    assert int(dut.blank_minutes.value) == 0, "blank_minutes must be 0 when seconds selected"
    assert int(dut.blank_hours.value)   == 0, "blank_hours must be 0 when seconds selected"

    # Verify blank_seconds is pulsing (not stuck at 0 or 1).
    cocotb.log.info("Section 3a: blank_seconds is pulsing")
    saw_high = False
    saw_low  = False
    for _ in range(PERIOD * 3):
        await tick(dut)
        v = int(dut.blank_seconds.value)
        if v == 1:
            saw_high = True
        if v == 0:
            saw_low = True
        if saw_high and saw_low:
            break
    assert saw_high and saw_low, "blank_seconds must toggle (not stuck) when seconds selected"

    # -----------------------------------------------------------------------
    # Section 4: verify PWM period and duty cycle on blank_seconds
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 4: verify blank_seconds PWM period and duty cycle")
    high_cycles, low_cycles = await measure_pwm(dut, dut.blank_seconds, PERIOD * 4)
    assert high_cycles == HIGH, (
        f"blank_seconds high duration: expected {HIGH} cycles, got {high_cycles}"
    )
    assert high_cycles + low_cycles == PERIOD, (
        f"blank_seconds PWM period: expected {PERIOD} cycles, got {high_cycles + low_cycles}"
    )

    # -----------------------------------------------------------------------
    # Section 5: short press advances selection to minutes
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 5: short press advances to minutes")
    await press(dut, 2)
    await tick_n(dut, 3)
    assert int(dut.blank_seconds.value) == 0, "blank_seconds must be 0 when minutes selected"
    assert int(dut.blank_hours.value)   == 0, "blank_hours must be 0 when minutes selected"

    # Verify blank_minutes is now pulsing with correct period.
    high_cycles, low_cycles = await measure_pwm(dut, dut.blank_minutes, PERIOD * 4)
    assert high_cycles == HIGH, (
        f"blank_minutes high duration: expected {HIGH}, got {high_cycles}"
    )
    assert high_cycles + low_cycles == PERIOD, (
        f"blank_minutes PWM period: expected {PERIOD}, got {high_cycles + low_cycles}"
    )

    # -----------------------------------------------------------------------
    # Section 6: short press advances selection to hours
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 6: short press advances to hours")
    await press(dut, 2)
    await tick_n(dut, 3)
    assert int(dut.blank_seconds.value) == 0, "blank_seconds must be 0 when hours selected"
    assert int(dut.blank_minutes.value) == 0, "blank_minutes must be 0 when hours selected"

    # Verify blank_hours is now pulsing with correct period.
    high_cycles, low_cycles = await measure_pwm(dut, dut.blank_hours, PERIOD * 4)
    assert high_cycles == HIGH, (
        f"blank_hours high duration: expected {HIGH}, got {high_cycles}"
    )
    assert high_cycles + low_cycles == PERIOD, (
        f"blank_hours PWM period: expected {PERIOD}, got {high_cycles + low_cycles}"
    )

    # -----------------------------------------------------------------------
    # Section 7: short press exits edit mode - all blank signals return to 0
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 7: short press exits edit mode")
    await press(dut, 2)
    await tick_n(dut, 3)
    assert int(dut.blank_seconds.value) == 0, "blank_seconds must be 0 after exiting edit mode"
    assert int(dut.blank_minutes.value) == 0, "blank_minutes must be 0 after exiting edit mode"
    assert int(dut.blank_hours.value)   == 0, "blank_hours must be 0 after exiting edit mode"
