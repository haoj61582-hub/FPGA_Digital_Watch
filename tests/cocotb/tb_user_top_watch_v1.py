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


def all_defined(dut):
    """Return True if the three time display outputs are fully resolved."""
    return all(
        sig.value.is_resolvable
        for sig in [dut.hours_disp, dut.minutes_disp, dut.seconds_disp]
    )


@cocotb.test()
async def test_timekeeping(dut):
    """Timekeeping: seconds count 0..59, roll over and carry into minutes and hours."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    dut.sw.value = 0
    await tick(dut)  # edge 1: allow initial register values to propagate

    CPS = int(dut.CYCLES_PER_SECOND.value)
    cocotb.log.info(f"CYCLES_PER_SECOND={CPS}")

    # -----------------------------------------------------------------------
    # Section 1: outputs defined and initial state is 00:00:00
    # -----------------------------------------------------------------------
    # The restartable_rate_generator first fires at edge CPS.  With CPS >= 2, edge 1 is
    # before any tick so all counters must still read zero.
    cocotb.log.info("Section 1: outputs defined; initial state is 00:00:00")
    assert all_defined(dut), "All display outputs must have no undefined bits at start"
    assert int(dut.seconds_disp.value) == 0, "seconds_disp should start at 0"
    assert int(dut.minutes_disp.value) == 0, "minutes_disp should start at 0"
    assert int(dut.hours_disp.value) == 0, "hours_disp should start at 0"

    # -----------------------------------------------------------------------
    # Section 2: seconds_disp advances every CPS clock edges
    # -----------------------------------------------------------------------
    # The k-th seconds tick fires at edge k*CPS.  We are at edge 1.
    cocotb.log.info(f"Section 2: seconds_disp advances every {CPS} cycles")
    await tick_n(dut, CPS - 1)           # total: CPS edges -> seconds = 1
    assert int(dut.seconds_disp.value) == 1, \
        f"seconds_disp should be 1 after {CPS} edges"
    await tick_n(dut, CPS)               # total: 2*CPS edges -> seconds = 2
    assert int(dut.seconds_disp.value) == 2, \
        f"seconds_disp should be 2 after {2 * CPS} edges"

    # -----------------------------------------------------------------------
    # Section 3: seconds rolls over 59->0 and minutes_disp increments
    # -----------------------------------------------------------------------
    # The 60th seconds tick fires at edge 60*CPS.  We are at edge 2*CPS.
    cocotb.log.info("Section 3: seconds rolls over 59->0; minutes_disp increments")
    await tick_n(dut, 58 * CPS)          # total: 60*CPS edges
    assert int(dut.seconds_disp.value) == 0, \
        "seconds_disp must wrap to 0 at the 60-second boundary"
    assert int(dut.minutes_disp.value) == 1, \
        "minutes_disp must increment to 1 when seconds rolls over"
    assert int(dut.hours_disp.value) == 0, \
        "hours_disp must remain 0 after only one minute"

    # -----------------------------------------------------------------------
    # Section 4: minutes rolls over 59->0 and hours_disp increments
    # -----------------------------------------------------------------------
    # The 60th minutes tick fires at edge 60*60*CPS.  We are at edge 60*CPS.
    cocotb.log.info("Section 4: minutes rolls over 59->0; hours_disp increments")
    await tick_n(dut, 59 * 60 * CPS)    # total: 60*60*CPS edges
    assert int(dut.hours_disp.value) == 1, \
        "hours_disp must increment to 1 when minutes rolls over"
    assert int(dut.minutes_disp.value) == 0, \
        "minutes_disp must wrap to 0 at the 60-minute boundary"
    assert int(dut.seconds_disp.value) == 0, \
        "seconds_disp must be 0 at an exact hour boundary"
