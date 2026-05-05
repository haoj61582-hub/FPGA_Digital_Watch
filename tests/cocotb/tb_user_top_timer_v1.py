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


async def press(dut, bit, cycles=2):
    """Hold button[bit] for `cycles` clock cycles, then release."""
    dut.button.value = dut.button.value.to_unsigned() | (1 << bit)
    await tick_n(dut, cycles)
    dut.button.value = dut.button.value.to_unsigned() & ~(1 << bit)
    await tick(dut)


@cocotb.test()
async def test_timer(dut):
    """Timer: initial state, start/stop, countdown, auto-stop at zero, and edit mode."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    dut.sw.value = 0
    await tick(dut)

    CPS = int(dut.CYCLES_PER_SECOND.value)
    HOLD = CPS       # long-press threshold for edit_mode_selector (one simulated second)
    SHORT = 2        # short press: below auto-repeat threshold; produces one pulse
    PWM_PERIOD = CPS // 2
    cocotb.log.info(f"CYCLES_PER_SECOND={CPS}  HOLD={HOLD}  SHORT={SHORT}  PWM_PERIOD={PWM_PERIOD}")

    # -----------------------------------------------------------------------
    # Section 1: outputs defined; initial state is 00:00:00, no blanking
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 1: initial state 00:00:00, no blanking")
    assert int(dut.seconds_disp.value) == 0, "seconds must start at 0"
    assert int(dut.minutes_disp.value) == 0, "minutes must start at 0"
    assert int(dut.hours_disp.value)   == 0, "hours must start at 0"
    assert int(dut.blank_seconds.value) == 0, "blank_seconds must be 0 initially"
    assert int(dut.blank_minutes.value) == 0, "blank_minutes must be 0 initially"
    assert int(dut.blank_hours.value)   == 0, "blank_hours must be 0 initially"

    # -----------------------------------------------------------------------
    # Section 2: pressing start at 00:00:00 does not start the timer
    # The running FF is held at 0 when at_zero is true.
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 2: start does nothing when at 00:00:00")
    await press(dut, 0, SHORT)
    await tick_n(dut, CPS + 3)
    assert int(dut.seconds_disp.value) == 0, "timer must not run when started at zero"
    assert int(dut.minutes_disp.value) == 0, "minutes must stay 0 when started at zero"

    # -----------------------------------------------------------------------
    # Section 3: long press button[3] enters edit mode - seconds field selected
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 3: long press enters seconds edit mode")
    await press(dut, 3, HOLD)
    await tick_n(dut, 3)
    assert int(dut.blank_minutes.value) == 0, "blank_minutes must be 0 when seconds selected"
    assert int(dut.blank_hours.value)   == 0, "blank_hours must be 0 when seconds selected"
    # blank_seconds must be pulsing (PWM); check we see at least one high within 2 periods
    saw_high = False
    for _ in range(PWM_PERIOD * 2 + 2):
        await tick(dut)
        if int(dut.blank_seconds.value) == 1:
            saw_high = True
            break
    assert saw_high, "blank_seconds must pulse high while seconds field is selected"

    # -----------------------------------------------------------------------
    # Section 4: increment seconds to 3 with three short button[1] presses
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 4: increment seconds to 3")
    for _ in range(3):
        await press(dut, 1, SHORT)
        await tick_n(dut, 3)
    assert int(dut.seconds_disp.value) == 3, "seconds must be 3 after three inc presses"
    assert int(dut.minutes_disp.value) == 0, "minutes must be unaffected by seconds inc"

    # -----------------------------------------------------------------------
    # Section 5: short press advances to minutes edit field
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 5: advance to minutes edit")
    await press(dut, 3, SHORT)
    await tick_n(dut, 3)
    assert int(dut.blank_seconds.value) == 0, "blank_seconds must be 0 when minutes selected"
    assert int(dut.blank_hours.value)   == 0, "blank_hours must be 0 when minutes selected"
    saw_high = False
    for _ in range(PWM_PERIOD * 2 + 2):
        await tick(dut)
        if int(dut.blank_minutes.value) == 1:
            saw_high = True
            break
    assert saw_high, "blank_minutes must pulse high while minutes field is selected"

    # -----------------------------------------------------------------------
    # Section 6: advance through hours edit and exit edit mode
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 6: advance to hours edit then exit")
    await press(dut, 3, SHORT)   # minutes -> hours
    await tick_n(dut, 3)
    assert int(dut.blank_seconds.value) == 0, "blank_seconds must be 0 when hours selected"
    assert int(dut.blank_minutes.value) == 0, "blank_minutes must be 0 when hours selected"

    await press(dut, 3, SHORT)   # hours -> exit
    await tick_n(dut, 3)
    assert int(dut.blank_seconds.value) == 0, "blank_seconds must be 0 after exiting edit"
    assert int(dut.blank_minutes.value) == 0, "blank_minutes must be 0 after exiting edit"
    assert int(dut.blank_hours.value)   == 0, "blank_hours must be 0 after exiting edit"

    # seconds is now 3; timer is not running
    assert int(dut.seconds_disp.value) == 3, "seconds must still be 3 after exiting edit"

    # -----------------------------------------------------------------------
    # Section 7: start the timer; verify seconds counts down
    # The first 1 Hz tick fires CPS edges after running goes high.
    # running goes high at the first rising edge of the start press.
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 7: start timer, verify seconds counts down")
    await press(dut, 0, SHORT)
    # After the press (3 edges) + CPS edges, the first tick has fired.
    await tick_n(dut, CPS)
    assert int(dut.seconds_disp.value) == 2, \
        "seconds must decrement to 2 after the first 1 Hz tick"

    # -----------------------------------------------------------------------
    # Section 8: stop mid-countdown; verify display freezes
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 8: stop mid-countdown")
    await press(dut, 0, SHORT)
    frozen = int(dut.seconds_disp.value)
    await tick_n(dut, CPS + 3)
    assert int(dut.seconds_disp.value) == frozen, \
        "seconds must not advance while the timer is stopped"

    # -----------------------------------------------------------------------
    # Section 9: restart and count all the way down to 00:00:00 (auto-stop)
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 9: restart and count to zero (auto-stop)")
    await press(dut, 0, SHORT)
    # Wait long enough for `frozen` remaining ticks plus margin
    await tick_n(dut, frozen * CPS + CPS + 5)
    assert int(dut.seconds_disp.value) == 0, "seconds must be 0 after counting to zero"
    assert int(dut.minutes_disp.value) == 0, "minutes must be 0 after counting to zero"
    assert int(dut.hours_disp.value)   == 0, "hours must be 0 after counting to zero"

    # -----------------------------------------------------------------------
    # Section 10: timer must have auto-stopped at zero; pressing start again
    # does nothing because at_zero holds running at 0
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 10: auto-stopped - start does nothing at 00:00:00")
    await press(dut, 0, SHORT)
    await tick_n(dut, CPS + 3)
    assert int(dut.seconds_disp.value) == 0, "timer must not restart from zero"
    assert int(dut.minutes_disp.value) == 0, "minutes must remain 0"
    assert int(dut.hours_disp.value)   == 0, "hours must remain 0"


@cocotb.test()
async def test_countdown_delay_and_period(dut):
    """First decrement is delayed CPS cycles after start; subsequent decrements are CPS cycles apart."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    dut.sw.value = 0
    await tick(dut)

    CPS = int(dut.CYCLES_PER_SECOND.value)
    HOLD = CPS
    SHORT = 2

    # Set up 00:00:03 via edit mode (DUT is at 00:00:00, not running)
    await press(dut, 3, HOLD)          # long press -> enter edit mode, seconds selected
    await tick_n(dut, 3)
    for _ in range(3):
        await press(dut, 1, SHORT)     # increment seconds
        await tick_n(dut, 3)
    await press(dut, 3, SHORT)         # seconds -> minutes
    await tick_n(dut, 3)
    await press(dut, 3, SHORT)         # minutes -> hours
    await tick_n(dut, 3)
    await press(dut, 3, SHORT)         # hours -> exit edit mode
    await tick_n(dut, 3)
    assert int(dut.seconds_disp.value) == 3, "setup: seconds must be 3 before timing test"

    # Press start.  running goes high at posedge 1 (inside press); the
    # restartable_rate_generator fires its first tick at posedge CPS+1 from
    # that edge, which is CPS-2 posedges after press() returns.
    await press(dut, 0, SHORT)

    # CPS-3 posedges after press: one posedge short of the first tick.
    await tick_n(dut, CPS - 3)
    assert int(dut.seconds_disp.value) == 3, \
        "seconds must not decrement before the initial CPS-cycle delay has elapsed"

    # 2 more posedges: the first tick has now fired.
    await tick_n(dut, 2)
    assert int(dut.seconds_disp.value) == 2, \
        "seconds must decrement to 2 after the initial CPS-cycle delay"

    # Each subsequent CPS-cycle period produces exactly one more decrement.
    await tick_n(dut, CPS)
    assert int(dut.seconds_disp.value) == 1, \
        "seconds must decrement to 1 after the second CPS-cycle period"

    await tick_n(dut, CPS)
    assert int(dut.seconds_disp.value) == 0, \
        "seconds must decrement to 0 after the third CPS-cycle period"
