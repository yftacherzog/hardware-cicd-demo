import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_alu_operations(dut):
    """Test all mathematical operations of the ALU"""
    
    # 1. Provide initial input data
    dut.a.value = 10
    dut.b.value = 5
    
    # 2. Test Addition (op code 0)
    dut.op.value = 0
    # Wait 1 nanosecond for the electrical signals to propagate
    await Timer(1, units="ns") 
    assert dut.result.value == 15, f"Addition failed! Got: {dut.result.value}"
    dut._log.info("Addition passed.")

    # 3. Test Subtraction (op code 1)
    dut.op.value = 1
    await Timer(1, units="ns")
    assert dut.result.value == 5, f"Subtraction failed! Got: {dut.result.value}"
    dut._log.info("Subtraction passed.")