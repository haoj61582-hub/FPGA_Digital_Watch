import os
import tempfile
from pathlib import Path

import pytest
from cocotb_tools.runner import get_runner

# Project root is one level up from this conftest.py file
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_rtl_root() -> Path:
    """Return RTL root directory from RTL_DIR env var or default to project rtl/."""
    rtl_dir = os.environ.get("RTL_DIR")
    if not rtl_dir:
        return PROJECT_ROOT / "rtl"

    path = Path(rtl_dir).expanduser()
    if path.is_absolute():
        return path.resolve()

    # Relative paths: try cwd first (standard Unix convention), then
    # project root as a fallback. This lets both "RTL_DIR=rtl_solution"
    # from the project root and "RTL_DIR=../rtl_solution" from tests/ work,
    # and avoids breaking when conftest is imported from a subprocess
    # (e.g. cocotb's pytest assertion-rewriting hook) with a different cwd.
    for base in (Path.cwd(), PROJECT_ROOT):
        candidate = (base / path).resolve()
        if candidate.is_dir():
            return candidate

    return (PROJECT_ROOT / path).resolve()


RTL_ROOT = get_rtl_root()


def get_default_build_dir() -> Path:
    """Return build directory from SIM_BUILD_DIR or a temp dir by default."""
    sim_build_dir = os.environ.get("SIM_BUILD_DIR")
    if sim_build_dir:
        path = Path(sim_build_dir).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    # Keep simulation artifacts out of the repository by default.
    return Path(tempfile.gettempdir()) / f"{PROJECT_ROOT.name}_sim_build"


def resolve_rtl_path(filename):
    """Convert source path to absolute path.

    Args:
        filename: Relative path (assumed in RTL_ROOT) or absolute path

    Returns:
        Absolute Path object
    """
    path = Path(filename)
    if path.is_absolute():
        return path
    else:
        return RTL_ROOT / filename


def resolve_sby_path(filename):
    path = Path(filename)
    if path.is_absolute():
        return path
    else:
        return PROJECT_ROOT / "sby" / filename


@pytest.fixture(scope="session")
def sim_name(pytestconfig):
    return pytestconfig.getoption("--sim")


def pytest_addoption(parser):
    parser.addoption(
        "--sim", action="store", default="icarus", help="HDL simulator to use"
    )
    parser.addoption(
        "--seed",
        action="store",
        default=None,
        type=int,
        help="Random seed for cocotb tests",
    )


def pytest_configure(config):
    seed = config.getoption("--seed", default=None)
    if seed is not None:
        os.environ["COCOTB_RANDOM_SEED"] = str(seed)


@pytest.fixture
def cocotb_runner(sim_name):
    def _run(*, top, sources, test_module, parameters=None, build_dir=None):
        runner = get_runner(sim_name)

        # Convert source paths to absolute paths using helper
        abs_sources = [resolve_rtl_path(src) for src in sources]

        # Default build_dir to temp location unless SIM_BUILD_DIR is set.
        if build_dir is None:
            build_dir = get_default_build_dir()

        runner.build(
            sources=abs_sources,
            hdl_toplevel=top,
            parameters=parameters or {},
            timescale=("1ns", "1ps"),
            build_dir=build_dir,
            always=True,
            build_args=["-y", str(RTL_ROOT), "-Y", ".sv"],
        )

        runner.test(
            hdl_toplevel=top,
            test_module=test_module,
            test_dir=PROJECT_ROOT / "tests" / "cocotb",
            build_dir=build_dir,
        )

    return _run


def rtl_exists(filename):
    """Check if an RTL file exists.

    Args:
        filename: Relative path (assumed in RTL_ROOT), e.g., "up_down_counter.v"
                  or absolute path for full control
    """
    return resolve_rtl_path(filename).exists()


def sby_exists(filename):
    """Check if a SymbiYosys spec file exists.

    Args:
        filename: Relative path (assumed in sby/), e.g., "mod_n_counter.sby"
                  or absolute path for full control
    """
    return resolve_sby_path(filename).exists()
