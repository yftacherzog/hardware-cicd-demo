import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, with_timeout
from enum import IntEnum
from collections import deque
import random

class AluOp(IntEnum):
    ADD = 0
    SUB = 1
    AND = 2
    OR = 3

# --- 1. Golden Reference Model ---
def alu_golden_model(a: int, b: int, op: AluOp) -> int:
    """Pure Python representation of what the hardware *should* do."""
    if op == AluOp.ADD:
        res = a + b
    elif op == AluOp.SUB:
        res = a - b
    elif op == AluOp.AND:
        res = a & b
    elif op == AluOp.OR:
        res = a | b
    else:
        res = 0
    return res & 0xFF  # Keep it constrained to 8 bits

# --- 2. Scoreboard ---
class AluScoreboard:
    """Queues expected results and verifies them against actual outputs."""
    def __init__(self, dut):
        self.dut = dut
        self.expected_results = deque()
        self.transactions_checked = 0

    def record_input(self, a: int, b: int, op: int):
        expected = alu_golden_model(a, b, AluOp(op))
        self.expected_results.append((a, b, op, expected))

    def check_output(self, actual: int):
        assert self.expected_results, "DUT produced an output, but no inputs were recorded!"
        a, b, op, expected = self.expected_results.popleft()

        assert actual == expected, (
            f"MISMATCH! Op: {AluOp(op).name}, A: {a}, B: {b} "
            f"| Expected: {expected} | Actual: {actual}"
        )
        self.dut._log.info(f"MATCH: {a:3} {AluOp(op).name:3} {b:3} = {actual:3}")
        self.transactions_checked += 1

# --- 3. Passive Monitors ---
async def input_monitor(dut, scoreboard):
    """Sniffs the input bus for valid handshakes."""
    while True:
        await FallingEdge(dut.clk)
        if dut.valid_in.value == 1 and dut.ready_in.value == 1:
            scoreboard.record_input(
                dut.a.value.integer,
                dut.b.value.integer,
                dut.op.value.integer
            )

async def output_monitor(dut, scoreboard):
    """Sniffs the output bus for valid handshakes."""
    while True:
        await FallingEdge(dut.clk)
        if dut.valid_out.value == 1 and dut.ready_out.value == 1:
            scoreboard.check_output(dut.result.value.integer)

# --- 4. Active Drivers ---
async def alu_driver(dut, a, b, op):
    """Pushes a single transaction into the DUT."""
    dut.a.value = a
    dut.b.value = b
    dut.op.value = op
    dut.valid_in.value = 1

    while True:
        await FallingEdge(dut.clk)
        if dut.ready_in.value == 1:
            break

    dut.valid_in.value = 0

async def alu_consumer(dut, ready_probability=0.7):
    """
    Acts as the downstream module. Randomly drops ready_out
    to test pipeline backpressure and stall logic.
    """
    while True:
        # Drive the signal on the falling edge (safe from race conditions)
        await FallingEdge(dut.clk)

        # ready_probability chance to be ready, otherwise stall
        if random.random() < ready_probability:
            dut.ready_out.value = 1
        else:
            dut.ready_out.value = 0
            dut._log.debug("Consumer STALL: ready_out = 0")

# --- 5. The Test ---
@cocotb.test()
async def test_alu_scoreboard(dut):
    # Setup clock
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

    # Initialize Verification Components
    scoreboard = AluScoreboard(dut)
    cocotb.start_soon(input_monitor(dut, scoreboard))
    cocotb.start_soon(output_monitor(dut, scoreboard))

    # Run the consumer with 50% probability to aggressively test backpressure
    cocotb.start_soon(alu_consumer(dut, ready_probability=0.5))

    # Test Phase 1: Directed Tests
    dut._log.info("--- Starting Directed Tests ---")
    await alu_driver(dut, 10, 5, AluOp.ADD)
    await alu_driver(dut, 20, 8, AluOp.SUB)

    # Test Phase 2: Constrained Random Testing
    dut._log.info("--- Starting Random Tests ---")
    num_random_tests = 15
    for _ in range(num_random_tests):
        a = random.randint(0, 255)
        b = random.randint(0, 255)
        op = random.choice(list(AluOp))
        await alu_driver(dut, a, b, op)

    # Wait for the pipeline to drain completely, dynamically handling any stalls
    total_expected = 2 + num_random_tests

    async def wait_for_drain():
        """Polls until all expected transactions are checked."""
        while scoreboard.transactions_checked < total_expected:
            await FallingEdge(dut.clk)

    try:
        # 1000 ns is plenty of time for 17 transactions even with heavy stalling
        await with_timeout(wait_for_drain(), 1000, "ns")
    except cocotb.result.SimTimeoutError:
        assert False, (
            f"Pipeline stalled forever! Checked {scoreboard.transactions_checked} "
            f"out of {total_expected}."
        )

    dut._log.info(f"SUCCESS! All {scoreboard.transactions_checked} transactions matched the golden model.")
