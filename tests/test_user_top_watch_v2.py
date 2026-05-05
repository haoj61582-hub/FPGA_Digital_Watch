import pytest
from conftest import rtl_exists

SOURCES = [
    "up_down_counter.sv",
    "restartable_rate_generator.sv",
    "editable_counter.sv",
    "rising_edge_detector.sv",
    "button_hold_detect.sv",
    "button_hold_pulse.sv",
    "arming_latch.sv",
    "mod_n_counter.sv",
    "edit_mode_selector.sv",
    "pwm_generator.sv",
    "user_top_watch_v2.sv",
]

# CYCLES_PER_SECOND=10 gives:
#   HOLD threshold = 10 cycles
#   PWM period     =  5 cycles  (2 Hz)
#   PWM high       =  1 cycle   (20% -> 80% display on)
CYCLES_PER_SECOND = 10


@pytest.mark.skipif(
    not rtl_exists("user_top_watch_v2.sv"),
    reason="user_top_watch_v2 module not implemented yet",
)
def test_user_top_watch_v2_timekeeping(cocotb_runner):
    """Timekeeping feature: seconds/minutes/hours counting and rollovers."""
    cocotb_runner(
        top="user_top_watch_v2",
        sources=SOURCES,
        test_module="tb_user_top_watch_v1",
        parameters={"CYCLES_PER_SECOND": CYCLES_PER_SECOND},
    )


@pytest.mark.skipif(
    not rtl_exists("user_top_watch_v2.sv"),
    reason="user_top_watch_v2 module not implemented yet",
)
def test_user_top_watch_v2_mode_selection(cocotb_runner):
    """Mode selection feature: long press, field cycling, PWM flashing."""
    cocotb_runner(
        top="user_top_watch_v2",
        sources=SOURCES,
        test_module="tb_user_top_watch_v2",
        parameters={"CYCLES_PER_SECOND": CYCLES_PER_SECOND},
    )
