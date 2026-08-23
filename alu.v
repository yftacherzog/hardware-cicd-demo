module alu (
    input wire clk,
    input wire rst,
    input wire [1:0] op,
    input wire [7:0] a,
    input wire [7:0] b,
    output reg [7:0] result
);

    // Define symbolic constants for operations
    localparam OP_ADD = 2'b00;
    localparam OP_SUB = 2'b01;
    localparam OP_AND = 2'b10;
    localparam OP_OR  = 2'b11;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            result <= 8'b0;
        end else begin
            case (op)
                OP_ADD:  result <= a + b;
                OP_SUB:  result <= a - b;
                OP_AND:  result <= a & b;
                OP_OR:   result <= a | b;
                default: result <= 8'b0;
            endcase
        end
    end

endmodule
