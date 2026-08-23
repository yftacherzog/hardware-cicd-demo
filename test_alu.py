import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge
from enum import IntEnum

class AluOp(IntEnum):
    ADD = 0
    SUB = 1
    AND = 2
    OR = 3

@cocotb.test()
async def test_alu_operations(dut):
    # 1. Start clock
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # 2. Reset sequence (Drive everything on falling edges)
    dut.rst.value = 1
    dut.op.value = AluOp.ADD
    dut.a.value = 0
    dut.b.value = 0

    await FallingEdge(dut.clk)
    await FallingEdge(dut.clk)

    dut.rst.value = 0
    dut._log.info("Reset released.")

    # 3. Test Addition
    # Apply inputs safely while clock is low
    dut.a.value = 10
    dut.b.value = 5
    dut.op.value = AluOp.ADD

    # Wait for the next falling edge.
    # During this wait, a RisingEdge occurs, the RTL captures inputs, and computes the result.
    await FallingEdge(dut.clk)

    # Now we are safely half a cycle past the computation. The result is perfectly stable.
    assert dut.result.value == 15, f"Addition failed! Got: {dut.result.value}"
    dut._log.info("Addition passed.")

    # 4. Test Subtraction
    # Seamlessly drive the next inputs immediately
    dut.a.value = 10
    dut.b.value = 5
    dut.op.value = AluOp.SUB

    await FallingEdge(dut.clk)

    assert dut.result.value == 5, f"Subtraction failed! Got: {dut.result.value}"
    dut._log.info("Subtraction passed.")
