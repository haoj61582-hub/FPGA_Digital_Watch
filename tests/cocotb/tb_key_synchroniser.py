import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def step(dut):
    """Advance one clock cycle and wait for registered outputs to settle."""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


@cocotb.test()
async def test_key_synchroniser(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.key_n.value = 0b1111  # all released (active-low)
    await Timer(1, unit="ns")

    # --- Test 0: port widths and initial values ---
    cocotb.log.info("Test 0: port widths are 4 bits and flip-flops initialise to zero")
    assert len(dut.key_sync) == 4, (
        f"key_sync should be 4 bits wide, got {len(dut.key_sync)}"
    )
    assert len(dut.key_n) == 4, f"key_n should be 4 bits wide, got {len(dut.key_n)}"
    assert int(dut.key_sync.value) == 0, (
        f"key_sync must be 0 at initialisation, got {int(dut.key_sync.value)}"
    )

    await RisingEdge(dut.clk)

    # --- Test 1: key_sync is 0 when all keys are released ---
    cocotb.log.info("Test 1: key_sync is 0 with all keys released")
    for _ in range(3):
        await step(dut)
        assert int(dut.key_sync.value) == 0, (
            "key_sync must be 0 when all keys are released"
        )

    # --- Test 2: active-low to active-high inversion ---
    # key_n low means key pressed; key_sync should go high.
    cocotb.log.info("Test 2: active-low to active-high inversion")
    dut.key_n.value = 0b1110  # key[0] pressed
    await step(dut)  # first FF captures
    await step(dut)  # second FF captures
    assert int(dut.key_sync.value) == 0b0001, (
        "key_sync[0] must be high when key_n[0] is low"
    )

    # --- Test 3: key_sync goes low 2 cycles after key is released ---
    cocotb.log.info("Test 3: key_sync deasserts 2 cycles after release")
    dut.key_n.value = 0b1111  # release key[0]
    await step(dut)
    assert int(dut.key_sync.value) == 0b0001, (
        "key_sync[0] must still be high one cycle after release"
    )
    await step(dut)
    assert int(dut.key_sync.value) == 0b0000, (
        "key_sync[0] must go low two cycles after release"
    )

    # --- Test 4: 2-cycle latency on assertion ---
    cocotb.log.info("Test 4: key_sync asserts 2 cycles after key press")
    dut.key_n.value = 0b1101  # key[1] pressed
    await step(dut)
    assert int(dut.key_sync.value) == 0b0000, (
        "key_sync[1] must still be low one cycle after press"
    )
    await step(dut)
    assert int(dut.key_sync.value) == 0b0010, (
        "key_sync[1] must go high two cycles after press"
    )
    dut.key_n.value = 0b1111
    await step(dut)
    await step(dut)

    # --- Test 5: all four channels are independent ---
    cocotb.log.info("Test 5: all four channels synchronise independently")
    for i in range(4):
        dut.key_n.value = ~(1 << i) & 0b1111  # press key[i] only
        await step(dut)
        await step(dut)
        assert int(dut.key_sync.value) == (1 << i), (
            f"key_sync[{i}] must be high when only key_n[{i}] is low, "
            f"got {int(dut.key_sync.value):#06b}"
        )
        dut.key_n.value = 0b1111  # release
        await step(dut)
        await step(dut)

    # --- Test 6: all keys pressed simultaneously ---
    cocotb.log.info("Test 6: all keys pressed simultaneously")
    dut.key_n.value = 0b0000
    await step(dut)
    await step(dut)
    assert int(dut.key_sync.value) == 0b1111, (
        "key_sync must be 0b1111 when all keys are pressed"
    )
    dut.key_n.value = 0b1111
    await step(dut)
    await step(dut)
    assert int(dut.key_sync.value) == 0b0000, (
        "key_sync must return to 0 after all keys are released"
    )
