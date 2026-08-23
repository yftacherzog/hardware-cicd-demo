# Hardware CI/CD Demo

A lightweight, modern template for hardware verification using **Cocotb**, **Verilator**, and **Pytest**, backed by automated GitHub Actions CI.

This repository demonstrates how to bridge the gap between hardware description languages (Verilog) and Python-driven software testing, ensuring assertion failures correctly propagate exit codes locally and in CI.

## Project Structure

* **`alu.v`** – The hardware design under test (DUT).
* **`test_alu.py`** – Pure Cocotb async test coroutine defining assertions and stimulus.
* **`test_alu_runner.py`** – Python-native test runner (`cocotb-test` + `pytest`) managing simulation compilation and execution.
* **`pyproject.toml`** – Project configuration and Python dependencies.
* **`.github/workflows/ci.yml`** – Automated CI pipeline checking test health and capturing waveforms.

## Prerequisites

* Python 3.12+
* Verilator
* Make / C++ compiler

## Local Development & Testing

1. **Install dependencies:**
   ```bash
   pip install .
