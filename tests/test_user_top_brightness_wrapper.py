import pytest
from conftest import rtl_exists

CONFIGS = [
    {"CYCLES_PER_SECOND": 8000},  # CyclesPerMS =  8 = 2^3       (tight 3-bit)
    {"CYCLES_PER_SECOND": 9000},  # CyclesPerMS =  9 = 2^3 + 1   (bit-width boundary)
    {"CYCLES_PER_SECOND": 16000},  # CyclesPerMS = 16 = 2^4      (tight 4-bit)
    {"CYCLES_PER_SECOND": 24000},  # CyclesPerMS = 24            (5-bit)
]

# user_top_brightness_wrapper wraps user_top and uses mod_n_counter directly.
# The template user_top has no sub-modules, so these three files are sufficient.
SOURCES = [
    "mod_n_counter.sv",
    "user_top.sv",
    "user_top_brightness_wrapper.sv",
]


@pytest.mark.skipif(
    not rtl_exists("user_top_brightness_wrapper.sv"),
    reason="user_top_brightness_wrapper not implemented yet",
)
@pytest.mark.parametrize(
    "config", CONFIGS, ids=lambda c: f"CPS{c['CYCLES_PER_SECOND']}"
)
def test_user_top_brightness_wrapper(cocotb_runner, config):
    """PWM period and duty-cycle ratio for all four brightness settings."""
    cocotb_runner(
        top="user_top_brightness_wrapper",
        sources=SOURCES,
        test_module="tb_user_top_brightness_wrapper",
        parameters=config,
    )
