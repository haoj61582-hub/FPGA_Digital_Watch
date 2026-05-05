import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def step(dut):
    """Advance one clock cycle and wait for combinational outputs to settle."""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


async def measure_period(signal, dut, timeout):
    """
    Measure the PWM period on *signal* by finding two consecutive rising edges
    (low->high).  Returns the period in clock cycles, or None if two edges are
    not found within *timeout* cycles.

    Edge-detection is used rather than phase assumptions, so the measurement
    is independent of where the PWM counter happens to be when called.
    """
    # Locate the first rising edge.
    prev = int(signal.value)
    for _ in range(timeout):
        await step(dut)
        curr = int(signal.value)
        if prev == 0 and curr == 1:
            break
        prev = curr
    else:
        return None  # no rising edge within timeout

    # Count clock cycles until the next rising edge.
    period = 0
    prev = 1
    for _ in range(timeout):
        await step(dut)
        period += 1
        curr = int(signal.value)
        if prev == 0 and curr == 1:
            return period
        prev = curr

    return None  # second rising edge not found within timeout


async def count_on_cycles(signal, dut, num_cycles):
    """
    Step *num_cycles* clock cycles and return how many times *signal* is 0
    (display not PWM-blanked).

    Over any window that is an exact multiple of the PWM period the on-count is
    independent of the starting phase: every counter value appears the same
    number of times regardless of where in the period sampling begins.
    """
    on = 0
    for _ in range(num_cycles):
        await step(dut)
        if int(signal.value) == 0:
            on += 1
    return on


@cocotb.test()
async def test_pwm_period_and_duty(dut):
    """
    Verify that user_top_brightness_wrapper applies the correct PWM blanking to
    all three display outputs: blank_hours, blank_minutes, and blank_seconds.

    The template user_top ties each blank output to the corresponding button bit:
      blank_hours   = button[0]
      blank_minutes = button[1]
      blank_seconds = button[2]

    Holding button = 0 makes orig_blank_* = 0 for all three outputs, so the
    wrapper outputs reduce to blanking_pwm directly.  Testing all three outputs
    catches a wrapper that accidentally applies the PWM blanking to fewer than
    all three outputs.

    Brightness settings (sw[9:8]):
      2'b00 -> 12.5 % on  (blanking threshold = CyclesPerMS / 8)
      2'b01 -> 25 %   on  (blanking threshold = CyclesPerMS / 4)
      2'b11 -> 50 %   on  (blanking threshold = CyclesPerMS / 2)
      2'b10 -> 100 %  on  (no PWM blanking - blanking_pwm is always 0)
    """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    dut.sw.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    CPS = int(dut.CYCLES_PER_SECOND.value)
    CPms = CPS // 1000  # PWM counter modulus = period in clock cycles

    cocotb.log.info(
        f"user_top_brightness_wrapper: CYCLES_PER_SECOND={CPS}, "
        f"PWM period={CPms} cycles"
    )

    # Named (signal-object, label) pairs - we run every sub-test for each.
    outputs = [
        (dut.blank_hours,   "blank_hours"),
        (dut.blank_minutes, "blank_minutes"),
        (dut.blank_seconds, "blank_seconds"),
    ]

    # sw[9:8] = sel -> full sw register value
    def sw_for(sel):
        return sel << 8

    # -----------------------------------------------------------------------
    # Test 0: full brightness (sw[9:8] = 2'b10) must never assert any output
    # blanking_pwm is 0 at full brightness, so blank_X = orig_blank_X = 0.
    # -----------------------------------------------------------------------
    cocotb.log.info(
        f"Test 0: full brightness (sw[9:8]=2'b10) - all blank outputs must "
        f"stay 0 for {CPms * 4} cycles"
    )
    dut.sw.value = sw_for(0b10)
    for cyc in range(CPms * 4):
        await step(dut)
        for sig, name in outputs:
            assert int(sig.value) == 0, (
                f"{name} went high at cycle {cyc} with full brightness "
                "(sw[9:8]=2'b10) - PWM must not add blanking at full brightness"
            )

    # -----------------------------------------------------------------------
    # Tests 1 & 2 for each dimmed brightness setting, repeated for every output
    # -----------------------------------------------------------------------
    # on_per_period mirrors the SV integer division used in the RTL:
    #   PWM12_5 = CyclesPerMS / 8  (display on when pwm_count < PWM12_5)
    #   PWM25   = CyclesPerMS / 4
    #   PWM50   = CyclesPerMS / 2
    cases = [
        (0b00, CPms // 8, "12.5%"),
        (0b01, CPms // 4, "25%"),
        (0b11, CPms // 2, "50%"),
    ]

    for sel, on_per_period, label in cases:
        off_per_period = CPms - on_per_period
        cocotb.log.info(
            f"=== Brightness {label} (sw[9:8]={sel:02b}) - "
            f"expect {on_per_period} on + {off_per_period} off "
            f"per {CPms}-cycle period ==="
        )

        dut.sw.value = sw_for(sel)
        await step(dut)  # let sw propagate through combinational blanking_pwm

        for sig, name in outputs:
            cocotb.log.info(f"  --- {name} ---")

            # --- Test 1: PWM period ---------------------------------------
            # Find two consecutive rising edges on the output (phase-independent).
            cocotb.log.info(
                f"  Test 1 ({label}, {name}): period must be exactly {CPms} cycles"
            )
            measured = await measure_period(sig, dut, timeout=CPms * 4)
            assert measured is not None, (
                f"Could not measure PWM period on {name} at {label} brightness - "
                f"no rising edge detected within {CPms * 4} cycles. "
                "Check that the mod-N counter drives all three blank outputs."
            )
            assert measured == CPms, (
                f"PWM period wrong on {name} at {label} brightness: "
                f"expected {CPms} cycles, got {measured} cycles"
            )

            # --- Test 2: on/off ratio over 16 complete periods ------------
            # Counting over an exact multiple of the PWM period makes the
            # result independent of starting phase.
            K = 16
            total_cycles = K * CPms
            expected_on = K * on_per_period
            cocotb.log.info(
                f"  Test 2 ({label}, {name}): {K} x {CPms} = {total_cycles} cycles"
                f" - expect {expected_on} on-cycles ({on_per_period}/{CPms} per period)"
            )
            on_count = await count_on_cycles(sig, dut, total_cycles)
            assert on_count == expected_on, (
                f"On/off ratio wrong on {name} at {label} brightness: "
                f"got {on_count} on-cycles out of {total_cycles} "
                f"(measured {on_count}/{total_cycles}), "
                f"expected {expected_on}/{total_cycles} "
                f"({on_per_period}/{CPms} per period)"
            )

