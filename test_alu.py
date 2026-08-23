import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, with_timeout
from enum import IntEnum

class AluOp(IntEnum):
    ADD = 0
    SUB = 1
    AND = 2
    OR = 3

async def alu_driver(dut, a, b, op):
    dut.a.value = a
    dut.b.value = b
    dut.op.value = op
    dut.valid_in.value = 1

    while True:
        await FallingEdge(dut.clk)
        if dut.ready_in.value == 1:
            break

    dut.valid_in.value = 0

async def alu_monitor(dut):
    dut.ready_out.value = 1
    while True:
        await FallingEdge(dut.clk)
        if dut.valid_out.value == 1:
            break
    res = dut.result.value
    dut.ready_out.value = 0
    return res

@cocotb.test()
async def test_alu_handshake(dut):
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Initialize / Reset
    dut.rst.value = 1
    dut.valid_in.value = 0
    dut.ready_out.value = 0
    await FallingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await FallingEdge(dut.clk)

    # Test 1: Run driver and monitor concurrently so backpressure is managed
    dut._log.info("Sending Addition...")

    # Start both simultaneously: the driver pushes data in, the monitor pulls data out
    driver_task = cocotb.start_soon(alu_driver(dut, 10, 5, AluOp.ADD))
    monitor_task = cocotb.start_soon(alu_monitor(dut))

    await with_timeout(driver_task, 100, "ns")
    result = await with_timeout(monitor_task, 100, "ns")

    assert result == 15, f"Addition failed! Got {result}"
    dut._log.info("Addition passed.")

    # Test 2: Subtraction
    dut._log.info("Sending Subtraction...")
    driver_task = cocotb.start_soon(alu_driver(dut, 20, 8, AluOp.SUB))
    monitor_task = cocotb.start_soon(alu_monitor(dut))

    await with_timeout(driver_task, 100, "ns")
    result = await with_timeout(monitor_task, 100, "ns")

    assert result == 12, f"Subtraction failed! Got {result}"
    dut._log.info("Subtraction passed.")
