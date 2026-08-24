from cocotb_test.simulator import run
import pytest

def test_alu():
    run(
        simulator="verilator",  # Add this line
        verilog_sources=["alu.v"],
        toplevel="alu",
        module="test_alu",
        extra_args=["--trace", "--trace-structs"],
    )
