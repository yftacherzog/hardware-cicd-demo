import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_alu_operations(dut):
    dut.a.value = 10
    dut.b.value = 5

    # Test Addition
    dut.op.value = 0
    await Timer(1, units="ns")
    assert dut.result.value == 15, f"Addition failed! Got: {dut.result.value}"

    # Test Subtraction
    dut.op.value = 1
    await Timer(1, units="ns")
    assert dut.result.value == 5, f"Subtraction failed! Got: {dut.result.value}"
