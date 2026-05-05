import re
import subprocess
import tempfile
from pathlib import Path

import pytest
from conftest import PROJECT_ROOT, RTL_ROOT, resolve_sby_path, rtl_exists, sby_exists

MODULES = [
    "cascade_counter",
    "editable_countdown",
    "snapshot_mux",
    "stopwatch_control",
    "stopwatch_counter",
    "up_down_counter_rst",
    "user_top_brightness_wrapper",
    "user_top_timer_v1",
]


@pytest.mark.formal
@pytest.mark.parametrize("module", MODULES)
def test_formal_sby(module):
    if not rtl_exists(module + ".sv"):
        pytest.skip(f"{module} module not implemented yet")
    if not sby_exists(module + ".sby"):
        pytest.skip(f"{module} sby spec not implemented yet")
    sby_filename = resolve_sby_path(module + ".sby")

    try:
        rtl_prefix = str(RTL_ROOT.relative_to(PROJECT_ROOT))
    except ValueError:
        rtl_prefix = str(RTL_ROOT)

    content = re.sub(
        r"^rtl/", f"{rtl_prefix}/", sby_filename.read_text(), flags=re.MULTILINE
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sby", delete=False) as f:
        f.write(content)
        tmp_sby = Path(f.name)

    try:
        result = subprocess.run(["sby", "-f", tmp_sby], check=False, cwd=PROJECT_ROOT)
    finally:
        tmp_sby.unlink(missing_ok=True)

    assert result.returncode == 0, "SBY failed!"
