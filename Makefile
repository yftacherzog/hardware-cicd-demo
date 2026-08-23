# Default simulator
SIM ?= verilator
TOPLEVEL_LANG ?= verilog

# Tell Verilator to generate a VCD waveform file
EXTRA_ARGS += --trace --trace-structs

# The Verilog file(s)
VERILOG_SOURCES += $(PWD)/alu.v

# The name of the top-level Verilog module to test
TOPLEVEL = alu

# The name of the Python test file (without the .py extension)
MODULE = test_alu

# Include Cocotb's standard make rules
include $(shell cocotb-config --makefiles)/Makefile.sim