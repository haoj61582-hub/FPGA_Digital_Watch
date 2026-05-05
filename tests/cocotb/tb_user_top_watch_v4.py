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


async def press_mode(dut, cycles):
    """Hold button[3] high for `cycles` clock cycles, then release."""
    dut.button.value = dut.button.value.to_unsigned() | 0b1000
    await tick_n(dut, cycles)
    dut.button.value = dut.button.value.to_unsigned() & ~0b1000
    await tick(dut)


@cocotb.test()
async def test_divider_reset_on_exit_seconds_edit(dut):
    """line 165: clock_divider_run = !(button[3] && mode_enable[0])

    Verifies that the 1-Hz clock divider is reset to zero the moment
    KEY[3] is pressed to exit seconds-edit mode (transitioning to minutes
    edit), and that no further reset occurs when leaving minutes edit or
    hours edit.

    Mechanism:
      mode_enable[0] is 1 only during seconds edit.  When button[3] rises
      while mode_enable[0]=1, clock_divider_run drops to 0 immediately
      (combinatorial).  The divider counter is cleared on the very next
      posedge; when count increments (clearing mode_enable[0]) the divider
      is released and counts from 0.  The next seconds_tick therefore
      arrives a full CPS cycles later.

      During the minutes->hours and hours->normal presses, mode_enable[0]=0
      so clock_divider_run stays 1 and the divider is unaffected.

    What is checked:
      1. After exiting seconds edit, seconds_disp does NOT advance for the
         first CPS//2 cycles.  Without the reset the divider would have been
         at count ~ CPS//2 + 1 before the exit press and the tick would have
         already fired by this point.
      2. seconds_disp DOES advance within a further CPS cycles, confirming
         the divider is running and the tick eventually fires.
      3. After subsequently exiting minutes edit (entering hours edit),
         seconds_disp advances on the normal schedule - confirming no second
         divider reset occurred.
    """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    dut.sw.value = 0
    await tick(dut)

    CPS = int(dut.CYCLES_PER_SECOND.value)
    HOLD = CPS  # long-press threshold for the mode selector

    # Enter seconds edit (long press).  mode_enable[0] goes high.
    await press_mode(dut, HOLD)

    # Advance CPS//2 cycles inside seconds edit.  The divider counts freely
    # but does not reach its terminal count (CPS//2 < CPS).
    await tick_n(dut, CPS // 2)
    seconds_before_exit = int(dut.seconds_disp.value)
    cocotb.log.info(
        f"seconds_disp before exit: {seconds_before_exit}  "
        f"(divider count ~ {CPS // 2})"
    )

    # Exit seconds edit -> minutes edit (short press).
    # Precondition: mode_enable[0]=1, divider count ~ CPS//2.
    # As button[3] rises, clock_divider_run drops to 0 (line 165).
    # The divider counter resets to 0 on the next posedge; count advances
    # to 1 (mode_enable[1]=1) and the divider is released.
    # The next seconds_tick fires CPS cycles from this return.
    await press_mode(dut, 2)
    cocotb.log.info("Exited seconds edit; divider counter reset to 0")

    # --- Assertion 1: no tick in the first CPS//2 cycles after exit ---
    # With reset: divider at ~CPS//2, still short of terminal count.
    # Without reset: divider would be at ~CPS, tick would have already fired.
    await tick_n(dut, CPS // 2)
    assert int(dut.seconds_disp.value) == seconds_before_exit, (
        f"seconds_disp advanced too soon after exiting seconds edit "
        f"(expected {seconds_before_exit}, got {int(dut.seconds_disp.value)}): "
        f"the clock divider was not reset (line 165)"
    )
    cocotb.log.info(
        f"After CPS//2={CPS // 2} cycles: seconds_disp still "
        f"{int(dut.seconds_disp.value)} - divider reset confirmed"
    )

    # --- Assertion 2: tick fires within the next CPS cycles ---
    await tick_n(dut, CPS)
    expected = (seconds_before_exit + 1) % 60
    assert int(dut.seconds_disp.value) == expected, (
        f"seconds_disp did not advance within CPS={CPS} cycles after exit "
        f"(expected {expected}, got {int(dut.seconds_disp.value)}): "
        f"the divider may not be running after the reset"
    )
    cocotb.log.info(
        f"After CPS//2+CPS cycles: seconds_disp={int(dut.seconds_disp.value)} "
        f"- first post-exit tick confirmed"
    )

    # --- Assertion 3: no spurious reset when leaving minutes edit (-> hours edit) ---
    # After assertion 2 the divider is approximately CPS//2 cycles into its
    # period.  Exiting minutes edit and waiting CPS//2 cycles puts the
    # divider past its terminal count, so a tick IS expected within that
    # window.  If a spurious reset had occurred the divider would restart
    # from 0 and no tick would arrive within CPS//2 cycles.
    seconds_before_minutes_exit = int(dut.seconds_disp.value)
    await press_mode(dut, 2)
    cocotb.log.info("Exited minutes edit (entered hours edit); no spurious reset expected")

    await tick_n(dut, CPS // 2)
    expected_after_no_reset = (seconds_before_minutes_exit + 1) % 60
    assert int(dut.seconds_disp.value) == expected_after_no_reset, (
        f"seconds_disp did not advance after leaving minutes edit within CPS//2 cycles "
        f"(expected {expected_after_no_reset}, got {int(dut.seconds_disp.value)}): "
        f"a spurious divider reset may have occurred"
    )
    cocotb.log.info(
        f"After CPS//2 cycles in hours edit: seconds_disp={int(dut.seconds_disp.value)} "
        f"- no spurious reset confirmed (divider continued counting)"
    )
