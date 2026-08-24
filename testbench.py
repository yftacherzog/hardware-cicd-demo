import cocotb
from cocotb.triggers import FallingEdge
from collections import deque
import random

# --- 1. Golden Model & Scoreboard ---
class RouterScoreboard:
    """Decodes packet headers and verifies packet payloads across all 4 output ports."""
    def __init__(self, dut):
        self.dut = dut
        self.expected_packets = {0: deque(), 1: deque(), 2: deque(), 3: deque()}
        self.packets_checked = 0

    def record_input_packet(self, packet: list[int]):
        """Decodes the header (first byte) to determine target port and queue expected packet."""
        assert len(packet) > 0, "Cannot route an empty packet!"
        header = packet[0]
        target_port = header & 0x03  # Low 2 bits dictate target port

        # Store a copy of the packet in the expected queue for that port
        self.expected_packets[target_port].append(list(packet))

    def check_output_packet(self, port_idx: int, actual_packet: list[int]):
        """Validates received packet against the expected queue for the target port."""
        queue = self.expected_packets[port_idx]
        assert queue, f"DUT produced packet on Port {port_idx}, but none was expected! Packet: {actual_packet}"

        expected_packet = queue.popleft()
        assert actual_packet == expected_packet, (
            f"MISMATCH on Port {port_idx}!\n"
            f"Expected: {expected_packet}\n"
            f"Actual:   {actual_packet}"
        )
        self.dut._log.info(f"[MATCH Port {port_idx}] Successfully routed {len(actual_packet)}-byte packet.")
        self.packets_checked += 1


# --- 2. Input Driver ---
async def axis_driver(dut, packet: list[int]):
    """Drives a full packet (list of bytes) into the s_axis interface."""
    for i, byte_val in enumerate(packet):
        dut.s_axis_tdata.value = byte_val
        dut.s_axis_tvalid.value = 1
        dut.s_axis_tlast.value = 1 if (i == len(packet) - 1) else 0

        # Wait until the handshake completes on the falling clock edge
        while True:
            await FallingEdge(dut.clk)
            if dut.s_axis_tready.value == 1:
                break

    # Clear signals after packet completes
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tlast.value = 0


# --- 3. Output Monitor ---
async def axis_monitor(dut, port_idx: int, scoreboard: RouterScoreboard):
    """Sniffs a specific master port for valid handshakes and reconstructs packets."""
    prefix = f"m0{port_idx}_axis"
    tvalid = getattr(dut, f"{prefix}_tvalid")
    tready = getattr(dut, f"{prefix}_tready")
    tdata  = getattr(dut, f"{prefix}_tdata")
    tlast  = getattr(dut, f"{prefix}_tlast")

    current_packet = []

    while True:
        await FallingEdge(dut.clk)
        if tvalid.value == 1 and tready.value == 1:
            current_packet.append(tdata.value.integer)
            if tlast.value == 1:
                scoreboard.check_output_packet(port_idx, current_packet)
                current_packet = []


# --- 4. Random-Stall Consumer ---
async def axis_consumer(dut, port_idx: int, ready_probability=0.7):
    """Drives tready for an output port, randomly toggling backpressure."""
    tready = getattr(dut, f"m0{port_idx}_axis_tready")

    while True:
        await FallingEdge(dut.clk)
        if random.random() < ready_probability:
            tready.value = 1
        else:
            tready.value = 0
