import os
from pathlib import Path
from cocotb_test.simulator import run
import pytest

def test_axis_router():
    sim_build = Path(__file__).resolve().parent / "sim_build_router"

    run(
        simulator="verilator",
        verilog_sources=["axis_router_1to4.v"],
        toplevel="axis_router_1to4",
        module="test_router",
        sim_build=str(sim_build),
        extra_args=[
            "--trace",
            "--trace-structs",
            "-Wno-fatal",
            "-Wno-WIDTH",
        ],
        waves=True,
    )
