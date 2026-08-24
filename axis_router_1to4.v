`timescale 1ns / 1ps

module axis_router_1to4 (
    input  wire       clk,
    input  wire       rst,

    // Slave (Input) AXI-Stream Interface
    input  wire       s_axis_tvalid,
    output wire       s_axis_tready,
    input  wire [7:0] s_axis_tdata,
    input  wire       s_axis_tlast,

    // Master 0 Output Interface
    output wire       m00_axis_tvalid,
    input  wire       m00_axis_tready,
    output wire [7:0] m00_axis_tdata,
    output wire       m00_axis_tlast,

    // Master 1 Output Interface
    output wire       m01_axis_tvalid,
    input  wire       m01_axis_tready,
    output wire [7:0] m01_axis_tdata,
    output wire       m01_axis_tlast,

    // Master 2 Output Interface
    output wire       m02_axis_tvalid,
    input  wire       m02_axis_tready,
    output wire [7:0] m02_axis_tdata,
    output wire       m02_axis_tlast,

    // Master 3 Output Interface
    output wire       m03_axis_tvalid,
    input  wire       m03_axis_tready,
    output wire [7:0] m03_axis_tdata,
    output wire       m03_axis_tlast
);

    // FSM States
    localparam STATE_IDLE  = 1'b0;
    localparam STATE_ROUTE = 1'b1;

    reg       state;
    reg [1:0] target_port_reg;

    // Active Port Selection:
    // In IDLE, decode the target port dynamically from the low 2 bits of the header byte.
    // In ROUTE, lock onto target_port_reg until the end of the packet (tlast).
    wire [1:0] current_port = (state == STATE_IDLE) ? s_axis_tdata[1:0] : target_port_reg;

    // Pack master ready signals into a vector for indexed bit operations
    wire [3:0] m_axis_tready_vec = {m03_axis_tready, m02_axis_tready, m01_axis_tready, m00_axis_tready};

    // Backpressure: Route ready from the selected output port back to the input port
    assign s_axis_tready = m_axis_tready_vec[current_port];

    // Assert valid ONLY on the currently targeted master port
    assign m00_axis_tvalid = (s_axis_tvalid && (current_port == 2'd0));
    assign m01_axis_tvalid = (s_axis_tvalid && (current_port == 2'd1));
    assign m02_axis_tvalid = (s_axis_tvalid && (current_port == 2'd2));
    assign m03_axis_tvalid = (s_axis_tvalid && (current_port == 2'd3));

    // Broadcast data and last signals to all master ports (valid gates acceptance)
    assign m00_axis_tdata = s_axis_tdata;
    assign m01_axis_tdata = s_axis_tdata;
    assign m02_axis_tdata = s_axis_tdata;
    assign m03_axis_tdata = s_axis_tdata;

    assign m00_axis_tlast = s_axis_tlast;
    assign m01_axis_tlast = s_axis_tlast;
    assign m02_axis_tlast = s_axis_tlast;
    assign m03_axis_tlast = s_axis_tlast;

    // FSM Sequential Control
    always @(posedge clk) begin
        if (rst) begin
            state           <= STATE_IDLE;
            target_port_reg <= 2'd0;
        end else begin
            case (state)
                STATE_IDLE: begin
                    // On a successful handshake for the first byte (header)
                    if (s_axis_tvalid && s_axis_tready) begin
                        if (!s_axis_tlast) begin
                            target_port_reg <= s_axis_tdata[1:0];
                            state           <= STATE_ROUTE;
                        end
                        // If tlast is high on the first byte (1-byte packet), stay in IDLE
                    end
                end

                STATE_ROUTE: begin
                    // On a successful handshake for remaining bytes
                    if (s_axis_tvalid && s_axis_tready) begin
                        if (s_axis_tlast) begin
                            state <= STATE_IDLE;
                        end
                    end
                end
            endcase
        end
    end

endmodule
