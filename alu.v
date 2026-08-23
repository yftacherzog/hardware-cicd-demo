module alu (
    input wire clk,
    input wire rst,

    // Input interface (from upstream)
    input wire [1:0] op,
    input wire [7:0] a,
    input wire [7:0] b,
    input wire valid_in,
    output wire ready_in,

    // Output interface (to downstream)
    output reg [7:0] result,
    output reg valid_out,
    input wire ready_out
);

    localparam OP_ADD = 2'b00;
    localparam OP_SUB = 2'b01;
    localparam OP_AND = 2'b10;
    localparam OP_OR  = 2'b11;

    // The ALU is ready to accept new data if the output register is empty,
    // OR if the output data is being successfully consumed this exact cycle.
    assign ready_in = !valid_out || ready_out;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            valid_out <= 1'b0;
            result <= 8'b0;
        end else begin
            // 1. Accept new data
            if (ready_in && valid_in) begin
                valid_out <= 1'b1;
                case (op)
                    OP_ADD:  result <= a + b;
                    OP_SUB:  result <= a - b;
                    OP_AND:  result <= a & b;
                    OP_OR:   result <= a | b;
                    default: result <= 8'b0;
                endcase
            end
            // 2. Clear output if data was consumed and no new data came in
            else if (ready_out && valid_out) begin
                valid_out <= 1'b0;
            end
        end
    end

endmodule
