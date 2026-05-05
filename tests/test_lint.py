"""
Lint and compilation checks for all RTL files.

Each .sv file is checked independently by both tools using a library search
path so that module dependencies are resolved without needing an explicit
source list per file.

  verilator --lint-only --Wall -I<rtl>   -- style, width, unused, ...
  iverilog  -g2012 -Wall -tnull -y<rtl>  -- syntax and elaboration errors
"""

import subprocess
from pathlib import Path

import pytest
from conftest import RTL_ROOT

SV_FILES = sorted(RTL_ROOT.glob("*.sv"))


def _verilator(sv_file: Path) -> str:
    result = subprocess.run(
        [
            "verilator",
            "--lint-only",
            "--Wall",
            "--sv",
            f"-I{RTL_ROOT}",
            str(sv_file),
        ],
        capture_output=True,
        text=True,
    )
    return result.stderr.strip()


def _iverilog(sv_file: Path) -> str:
    result = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-Wall",
            "-tnull",
            "-y",
            str(RTL_ROOT),
            "-Y",
            ".sv",
            str(sv_file),
        ],
        capture_output=True,
        text=True,
    )
    return (result.stdout + result.stderr).strip()


@pytest.mark.parametrize("sv_file", SV_FILES, ids=lambda p: p.name)
def test_verilator(sv_file):
    output = _verilator(sv_file)
    assert not output, f"verilator warnings/errors:\n{output}"


@pytest.mark.parametrize("sv_file", SV_FILES, ids=lambda p: p.name)
def test_iverilog(sv_file):
    output = _iverilog(sv_file)
    assert not output, f"iverilog warnings/errors:\n{output}"
