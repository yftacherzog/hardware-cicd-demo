import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer, with_timeout
from collections import deque
import random

# ==============================================================================
# 1. VERIFICATION INFRASTRUCTURE
# ==============================================================================

class RouterScoreboard:
    """Decodes packet headers and verifies packet payloads across all 4 output ports."""
    def __init__(self, dut):
        self.dut = dut
        self.expected_packets = {0: deque(), 1: deque(), 2: deque(), 3: deque()}
        self.packets_checked = 0

    def record_input_packet(self, packet: list[int]):
        assert len(packet) > 0, "Cannot route an empty packet!"
        header = packet[0]
        target_port = header & 0x03  # Low 2 bits dictate target port
        self.expected_packets[target_port].append(list(packet))

    def check_output_packet(self, port_idx: int, actual_packet: list[int]):
        queue = self.expected_packets[port_idx]
        assert queue, f"DUT produced packet on Port {port_idx}, but none expected! Packet: {actual_packet}"

        expected_packet = queue.popleft()
        assert actual_packet == expected_packet, (
            f"MISMATCH on Port {port_idx}!\n"
            f"Expected: {expected_packet}\n"
            f"Actual:   {actual_packet}"
        )
        self.dut._log.info(f"[MATCH Port {port_idx}] Successfully routed {len(actual_packet)}-byte packet.")
        self.packets_checked += 1


async def axis_driver(dut, scoreboard: RouterScoreboard, packet: list[int]):
    """Drives a packet byte-by-byte into the s_axis interface on clock falling edges."""
    scoreboard.record_input_packet(packet)

    for i, byte_val in enumerate(packet):
        await FallingEdge(dut.clk)
        dut.s_axis_tdata.value = byte_val
        dut.s_axis_tvalid.value = 1
        dut.s_axis_tlast.value = 1 if (i == len(packet) - 1) else 0

        while True:
            await RisingEdge(dut.clk)
            if dut.s_axis_tready.value == 1:
                break

    await FallingEdge(dut.clk)
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tlast.value = 0


async def axis_monitor(dut, port_idx: int, scoreboard: RouterScoreboard):
    """Sniffs a specific master port on clock rising edges and reconstructs packets."""
    prefix = f"m0{port_idx}_axis"
    tvalid = getattr(dut, f"{prefix}_tvalid")
    tready = getattr(dut, f"{prefix}_tready")
    tdata  = getattr(dut, f"{prefix}_tdata")
    tlast  = getattr(dut, f"{prefix}_tlast")

    current_packet = []

    while True:
        await RisingEdge(dut.clk)
        if tvalid.value == 1 and tready.value == 1:
            current_packet.append(tdata.value.integer)
            if tlast.value == 1:
                scoreboard.check_output_packet(port_idx, current_packet)
                current_packet = []


async def axis_consumer(dut, port_idx: int, ready_probability=0.7):
    """Drives tready for an output port with configurable random backpressure."""
    tready = getattr(dut, f"m0{port_idx}_axis_tready")

    while True:
        await FallingEdge(dut.clk)
        tready.value = 1 if (random.random() < ready_probability) else 0


async def setup_testbench(dut, ready_probability=0.7):
    """Helper to initialize clock, reset DUT, scoreboard, and background tasks."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    dut.rst.value = 1
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tlast.value = 0
    dut.s_axis_tdata.value = 0

    for i in range(4):
        getattr(dut, f"m0{i}_axis_tready").value = 0

    await FallingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await FallingEdge(dut.clk)

    scoreboard = RouterScoreboard(dut)

    for i in range(4):
        cocotb.start_soon(axis_monitor(dut, i, scoreboard))
        cocotb.start_soon(axis_consumer(dut, i, ready_probability))

    return scoreboard


async def wait_for_drain(dut, scoreboard, total_expected, timeout_ns=50000):
    """Polls until all expected packets pass through the scoreboard."""
    async def drain_loop():
        while scoreboard.packets_checked < total_expected:
            await RisingEdge(dut.clk)

    try:
        await with_timeout(drain_loop(), timeout_ns, "ns")
    except Exception:
        assert False, (
            f"Test Timeout! Checked {scoreboard.packets_checked} out of {total_expected} expected packets."
        )


# ==============================================================================
# 2. TEST CASES (PHASE 3)
# ==============================================================================

@cocotb.test()
async def test_directed_routing(dut):
    """Test 1: Verify header decoding routes packets to ports 0, 1, 2, and 3 correctly."""
    scoreboard = await setup_testbench(dut, ready_probability=1.0)
    dut._log.info("--- Starting Test 1: Directed Routing ---")

    test_packets = [
        [0x00, 0xAA, 0xBB, 0xCC],  # Target Port 0
        [0x01, 0x11, 0x22, 0x33],  # Target Port 1
        [0x02, 0x44, 0x55, 0x66],  # Target Port 2
        [0x03, 0x77, 0x88, 0x99],  # Target Port 3
    ]

    for pkt in test_packets:
        await axis_driver(dut, scoreboard, pkt)

    await wait_for_drain(dut, scoreboard, total_expected=len(test_packets))


@cocotb.test()
async def test_jumbo_packets(dut):
    """Test 2: Verify router handles 1-byte packets up to 1,000-byte jumbo frames."""
    scoreboard = await setup_testbench(dut, ready_probability=0.8)
    dut._log.info("--- Starting Test 2: Jumbo & Variable Length Packets ---")

    sizes = [1, 2, 16, 256, 1000]
    total_packets = 0

    for size in sizes:
        for port in range(4):
            header = (random.randint(0, 63) << 2) | port
            payload = [random.randint(0, 255) for _ in range(size - 1)]
            pkt = [header] + payload

            await axis_driver(dut, scoreboard, pkt)
            total_packets += 1

    await wait_for_drain(dut, scoreboard, total_expected=total_packets, timeout_ns=100000)


@cocotb.test()
async def test_head_of_line_blocking(dut):
    """Test 3: Verify backpressure propagation stalls input without losing state or data."""
    scoreboard = await setup_testbench(dut, ready_probability=0.0)
    dut._log.info("--- Starting Test 3: Head-of-Line Blocking ---")

    target_port = 0
    packet = [target_port, 0xDE, 0xAD, 0xBE, 0xEF]

    driver_task = cocotb.start_soon(axis_driver(dut, scoreboard, packet))

    for _ in range(20):
        await RisingEdge(dut.clk)
        assert dut.s_axis_tready.value == 0, "Input port failed to stall during downstream backpressure!"

    dut._log.info("Port 0 stalled for 20 cycles as expected. Enabling consumer...")

    getattr(dut, f"m0{target_port}_axis_tready").value = 1
    cocotb.start_soon(axis_consumer(dut, target_port, ready_probability=1.0))

    await driver_task
    await wait_for_drain(dut, scoreboard, total_expected=1)


@cocotb.test()
async def test_zero_bubble_back_to_back(dut):
    """Test 4: Stream packets with zero idle clock cycles between tlast and next tvalid."""
    scoreboard = await setup_testbench(dut, ready_probability=1.0)
    dut._log.info("--- Starting Test 4: Zero-Bubble Back-to-Back Packets ---")

    num_packets = 20
    packets = []

    for i in range(num_packets):
        port = i % 4
        pkt = [port, random.randint(0, 255), random.randint(0, 255)]
        packets.append(pkt)
        scoreboard.record_input_packet(pkt)

    for pkt in packets:
        for i, byte_val in enumerate(pkt):
            await FallingEdge(dut.clk)
            dut.s_axis_tdata.value = byte_val
            dut.s_axis_tvalid.value = 1
            dut.s_axis_tlast.value = 1 if (i == len(pkt) - 1) else 0

            while True:
                await RisingEdge(dut.clk)
                if dut.s_axis_tready.value == 1:
                    break

    await FallingEdge(dut.clk)
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tlast.value = 0

    await wait_for_drain(dut, scoreboard, total_expected=num_packets)
