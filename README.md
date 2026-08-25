# Hardware CI/CD Demo

A lightweight, modern template for hardware verification featuring an **8-bit ALU** and a **1-to-4 AXI4-Stream Packet Router**. Verified using **Cocotb**, **Verilator**, and **Pytest**, backed by automated GitHub Actions CI.

This repository demonstrates how to bridge hardware description languages (Verilog) with Python-driven software testing, ensuring assertion failures correctly propagate exit codes locally and in CI while generating visual waveform traces.

## Hardware Designs Under Test

### 1. 1-to-4 AXI-Stream Packet Router (`axis_router_1to4.v`)

A parameterized packet router accepting streaming data on a single slave port and dynamically routing each packet to one of four master output ports based on the initial header byte.

```text
                  +----------------------+---> Master 0 (Port 0)
                  |                      |---> Master 1 (Port 1)
Slave Input =====>|  AXI-Stream Router   |
(AXI4-Stream)     |       (1-to-4)       |---> Master 2 (Port 2)
                  |                      |---> Master 3 (Port 3)
                  +----------------------+
```

* **Protocol:** AXI4-Stream (`tdata`, `tvalid`, `tready`, `tlast`).
* **Routing Logic:** Header byte determines destination (`header[1:0]` maps to Ports 0–3).
* **State Machine:**
  * `IDLE`: Decodes header byte to select and lock in target destination port.
  * `ROUTE`: Streams payload bytes and multiplexes handshake signals until `tlast` assertion completes the transaction.
* **Backpressure Propagation:** Active master port `tready` propagates back to slave `tready` to stall upstream drivers during downstream bottlenecks.

### 2. 8-Bit ALU (`alu.v`)
An 8-bit Arithmetic Logic Unit supporting addition, subtraction, AND, OR, and XOR operations, serving as a baseline verification module.

## Verification Suite (Cocotb + Pytest)
The testbench architecture leverages Cocotb drivers, passive monitors, and Python scoreboards to validate hardware performance against golden models.

| Module | Test Case | Description | Verification Objective |
| :--- | :--- | :--- | :--- |
| **ALU** | **Scoreboard Test** | Directed and constrained random operations | Verifies arithmetic operations and pipeline output. |
| **Router** | **Directed Routing** | 4 packets targeted across Ports 0, 1, 2, and 3 | Validates header decoding and channel isolation. |
| **Router** | **Jumbo Packets** | Payloads ranging from 1 byte to 1,000 bytes | Verifies `tlast` boundary handling and payload integrity. |
| **Router** | **HOL Blocking** | Forced 20-cycle stall on active output port | Confirms backpressure propagates upstream without data loss. |
| **Router** | **Zero-Bubble** | Continuous stream of 20 packets with 0 idle cycles | Ensures seamless `ROUTE` -> `IDLE` -> `ROUTE` single-cycle state transitions. |

## CI/CD Pipeline (GitHub Actions)
Automated verification runs on every push and pull request via `.github/workflows/ci.yml`:
* **Environment Setup:** Configures Ubuntu, Python 3.12, Verilator, and system dependencies (`zlib1g-dev`, `g++`, `make`) with Pip caching enabled.
* **Test Isolation:** Configured `pyproject.toml` restricts Pytest collection to `*_runner.py` files to prevent fixture collisions with Cocotb coroutines.
* **Artifact Preservation:** Simulation trace dumps (`*.vcd`, `*.fst`) and JUnit test summaries (`results.xml`) are uploaded automatically on workflow completion.

## Local Development & Testing

### Prerequisites
* Python 3.12+
* Verilator
* Make / C++ compiler (`g++`)
* `zlib1g-dev`

### Setup & Execution
1. **Install dependencies:**
   ```bash
   pip install .
   ```
2. **Run full verification suite:**
   ```bash
   pytest -v
   ```
