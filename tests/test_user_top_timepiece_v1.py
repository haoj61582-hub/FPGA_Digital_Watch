import pytest
from conftest import rtl_exists

SOURCES = [
    "mod_n_counter.sv",
    "restartable_rate_generator.sv",
    "rising_edge_detector.sv",
    "edit_mode_selector.sv",
    "pwm_generator.sv",
    "button_auto_repeat.sv",
    "button_hold_detect.sv",
    "button_hold_pulse.sv",
    "arming_latch.sv",
    "up_down_counter_rst.sv",
    "up_down_counter.sv",
    "editable_counter.sv",
    "editable_countdown.sv",
    "cascade_counter.sv",
    "snapshot_mux.sv",
    "stopwatch_control.sv",
    "stopwatch_counter.sv",
    "user_top_watch_v4.sv",
    "user_top_timer_v1.sv",
    "user_top_stopwatch_v1.sv",
    "user_top_timepiece_v1.sv",
]


@pytest.mark.skipif(
    not rtl_exists("user_top_timepiece_v1.sv"),
    reason="user_top_timepiece_v1 not implemented yet",
)
def test_user_top_timepiece_v1(cocotb_runner):
    """Output routing and button isolation for the timepiece mode multiplexer."""
    cocotb_runner(
        top="user_top_timepiece_v1",
        sources=SOURCES,
        test_module="tb_user_top_timepiece_v1",
        parameters={"CYCLES_PER_SECOND": 200},
    )
