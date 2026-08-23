from cocotb_test.simulator import run
import pytest

def test_alu():
    run(
        verilog_sources=["alu.v"],
        toplevel="alu",
        module="test_alu",  # Loads test_alu.py above
        extra_args=["--trace", "--trace-structs"],
    )
