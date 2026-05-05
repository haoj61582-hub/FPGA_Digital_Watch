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


async def press(dut, bit):
    """Single button press: assert button[bit] for one cycle then release."""
    dut.button.value = 1 << bit
    await tick(dut)
    dut.button.value = 0
    await tick(dut)


@cocotb.test()
async def test_timepiece_mux(dut):
    """
    Verify all four contracts of the mode multiplexer:

      1. Output routing    -- sw[1:0] selects which app drives the outputs
      2. Button isolation  -- inactive apps receive no button presses
           2a: watch-mode button[0] presses do not start the stopwatch
           2b: timer-mode button[0] press does not start the stopwatch
           2c: stopwatch-mode button[3] hold does not put watch or timer into edit mode
      3. Button routing    -- the active app does receive button presses
      4. Continuous run    -- inactive apps keep running while not displayed
      5. State preserved   -- an app's state is intact when it becomes active again
    """
    CPS = int(dut.CYCLES_PER_SECOND.value)

    dut.button.value = 0
    await Timer(1, unit="ns")
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.sw.value = 0
    await tick(dut)

    # -----------------------------------------------------------------------
    # Section 1: output routing  -- sw[1:0] selects the correct app
    # -----------------------------------------------------------------------

    cocotb.log.info(f"Section 1: sw[1:0]=00 (watch)  -- wait {CPS} cycles, expect seconds=1")
    await tick_n(dut, CPS)
    assert int(dut.seconds_disp.value) == 1, (
        f"sw[1:0]=00 (watch): expected seconds=1 after {CPS} cycles, "
        f"got {int(dut.seconds_disp.value)}"
    )

    cocotb.log.info("Section 1: sw[1:0]=01 (stopwatch)  -- not started, expect seconds=0")
    dut.sw.value = 0b01
    await tick(dut)
    assert int(dut.seconds_disp.value) == 0, (
        f"sw[1:0]=01 (stopwatch): expected seconds=0 (not started), "
        f"got {int(dut.seconds_disp.value)}"
    )

    cocotb.log.info("Section 1: sw[1:0]=11 (timer)  -- at 0, expect seconds=0")
    dut.sw.value = 0b11
    await tick(dut)
    assert int(dut.seconds_disp.value) == 0, (
        f"sw[1:0]=11 (timer): expected seconds=0, "
        f"got {int(dut.seconds_disp.value)}"
    )

    cocotb.log.info("Section 1: sw[1:0]=10 (watch/default)  -- expect seconds>=1")
    dut.sw.value = 0b10
    await tick(dut)
    assert int(dut.seconds_disp.value) >= 1, (
        f"sw[1:0]=10 (watch/default): expected seconds>=1, "
        f"got {int(dut.seconds_disp.value)}"
    )

    dut.sw.value = 0b00
    await tick(dut)
    assert int(dut.seconds_disp.value) >= 1, (
        f"sw[1:0]=00 (watch return): expected seconds>=1, "
        f"got {int(dut.seconds_disp.value)}"
    )

    # -----------------------------------------------------------------------
    # Section 2: button isolation  -- inactive apps receive no button presses
    # -----------------------------------------------------------------------

    # 2a: four button[0] presses in MODE_WATCH must not start the stopwatch.
    # Four presses toggle start/stop four times (net: stopped), so if buttons
    # leaked the centiseconds counter will have accumulated a non-zero value
    # even though the stopwatch is currently paused.
    cocotb.log.info("Section 2a: press button[0] x4 while in MODE_WATCH")
    dut.sw.value = 0b00  # MODE_WATCH
    for _ in range(4):
        await press(dut, 0)

    cocotb.log.info(f"Section 2a: switch to MODE_STOPWATCH, wait {CPS} cycles")
    dut.sw.value = 0b01  # MODE_STOPWATCH
    await tick_n(dut, CPS)
    assert int(dut.seconds_disp.value) == 0, (
        f"Stopwatch centiseconds={int(dut.seconds_disp.value)} after {CPS} idle cycles: "
        "stopwatch appears to have run  -- button presses leaked from MODE_WATCH"
    )
    cocotb.log.info("Section 2a: stopwatch correctly isolated  -- centiseconds=0")

    # 2b: one button[0] press in MODE_TIMER must not start the stopwatch.
    # One press (odd count) would leave the stopwatch running if buttons leaked,
    # advancing elapsed seconds to 1.  Use minutes_disp (seconds elapsed, 0-59)
    # rather than seconds_disp (centiseconds, 0-99): centiseconds wraps back to
    # exactly 0 after CPS cycles of running and cannot distinguish started vs not.
    cocotb.log.info("Section 2b: press button[0] once in MODE_TIMER")
    dut.sw.value = 0b11  # MODE_TIMER
    await press(dut, 0)

    cocotb.log.info(f"Section 2b: switch to MODE_STOPWATCH, wait {CPS} cycles")
    dut.sw.value = 0b01  # MODE_STOPWATCH
    await tick_n(dut, CPS)
    assert int(dut.minutes_disp.value) == 0, (
        f"Stopwatch elapsed_seconds={int(dut.minutes_disp.value)} after {CPS} idle cycles: "
        "stopwatch appears to have started  -- button[0] leaked from MODE_TIMER"
    )
    cocotb.log.info("Section 2b: stopwatch correctly isolated  -- elapsed_seconds=0")

    # 2c: holding button[3] for CPS+1 cycles in MODE_STOPWATCH must not put the
    # watch or timer into edit mode.  The stopwatch ignores button[3] entirely so
    # it is unaffected; watch and timer must receive button[3]=0 (isolated).
    # blank_seconds going high (PWM blinking) signals edit mode was triggered.
    # Sample across a full PWM period (CPS//2 + 1 cycles) to guarantee detection.
    cocotb.log.info("Section 2c: hold button[3] for CPS+1 cycles in MODE_STOPWATCH")
    dut.sw.value = 0b01  # MODE_STOPWATCH
    dut.button.value = 0b1000  # button[3]
    await tick_n(dut, CPS + 1)
    dut.button.value = 0

    pwm_period = CPS // 2 + 1

    cocotb.log.info("Section 2c: check watch not in edit mode")
    dut.sw.value = 0b00  # MODE_WATCH
    for _ in range(pwm_period):
        await tick(dut)
        assert int(dut.blank_seconds.value) == 0, (
            "watch blank_seconds went high  -- button[3] hold leaked from "
            "MODE_STOPWATCH into the watch (edit mode triggered)"
        )

    cocotb.log.info("Section 2c: check timer not in edit mode")
    dut.sw.value = 0b11  # MODE_TIMER
    for _ in range(pwm_period):
        await tick(dut)
        assert int(dut.blank_seconds.value) == 0, (
            "timer blank_seconds went high  -- button[3] hold leaked from "
            "MODE_STOPWATCH into the timer (edit mode triggered)"
        )
    cocotb.log.info("Section 2c: watch and timer correctly isolated")

    # -----------------------------------------------------------------------
    # Section 3: button routing  -- the active app receives button presses
    # -----------------------------------------------------------------------

    # Press button[0] while already in MODE_STOPWATCH  -- this must start it.
    # A mux that silences all buttons would pass Section 2 but fail here.
    #
    # Note: in stopwatch mode seconds_disp carries centiseconds (0-99, wraps every
    # second), so checking it after exactly CPS cycles would always read 0.
    # minutes_disp carries actual seconds elapsed (0-59) and is the right signal.
    cocotb.log.info("Section 3: press button[0] while in MODE_STOPWATCH to start it")
    dut.sw.value = 0b01  # MODE_STOPWATCH
    await press(dut, 0)  # start

    cocotb.log.info(f"Section 3: wait {CPS} cycles, stopwatch must have advanced")
    await tick_n(dut, CPS)
    assert int(dut.minutes_disp.value) > 0, (
        f"Stopwatch elapsed_seconds={int(dut.minutes_disp.value)} after {CPS} cycles: "
        "stopwatch did not start  -- button[0] not reaching the active app"
    )
    cocotb.log.info(f"Section 3: stopwatch running  -- elapsed_seconds={int(dut.minutes_disp.value)}")

    # -----------------------------------------------------------------------
    # Section 4: continuous run  -- inactive apps keep running while not shown
    # -----------------------------------------------------------------------

    # Watch has been running since t=0. Switch to stopwatch for a full second,
    # then return; the watch must have advanced by one more second.
    cocotb.log.info("Section 4: record watch seconds, leave for one second in stopwatch")
    dut.sw.value = 0b00  # MODE_WATCH
    await tick(dut)
    watch_before = int(dut.seconds_disp.value)

    dut.sw.value = 0b01  # MODE_STOPWATCH  -- watch runs unseen
    await tick_n(dut, CPS)

    dut.sw.value = 0b00  # back to watch
    await tick(dut)
    watch_after = int(dut.seconds_disp.value)
    assert watch_after == watch_before + 1, (
        f"Watch went from {watch_before}s to {watch_after}s after {CPS} cycles away: "
        "expected exactly +1s  -- watch may have paused while inactive"
    )
    cocotb.log.info(f"Section 4: watch advanced {watch_before}s -> {watch_after}s while inactive")

    # -----------------------------------------------------------------------
    # Section 5: state preserved  -- app state survives a mode switch away and back
    # -----------------------------------------------------------------------

    # Stopwatch is currently running (started in Section 3).
    # Switch to watch briefly, then return; stopwatch must still be running.
    # Use minutes_disp (seconds elapsed, 0-59)  -- seconds_disp is centiseconds
    # (0-99 wrapping) and would wrap back to the same value after exactly CPS cycles.
    cocotb.log.info("Section 5: stopwatch is running  -- switch to watch and back")
    dut.sw.value = 0b01  # MODE_STOPWATCH
    await tick(dut)
    sw_before = int(dut.minutes_disp.value)

    dut.sw.value = 0b00  # MODE_WATCH  -- stopwatch runs unseen
    await tick_n(dut, CPS)

    dut.sw.value = 0b01  # back to stopwatch
    await tick(dut)
    sw_after = int(dut.minutes_disp.value)
    assert sw_after > sw_before, (
        f"Stopwatch elapsed_seconds went from {sw_before} to {sw_after} after {CPS} cycles away: "
        "expected it to have advanced  -- stopwatch may have been reset or paused"
    )
    cocotb.log.info(
        f"Section 5: stopwatch state preserved  -- {sw_before}s -> {sw_after}s"
    )
