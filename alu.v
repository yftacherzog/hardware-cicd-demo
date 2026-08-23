`timescale 1ns/1ps

module alu (
    input  wire [7:0] a,       // 8-bit input A
    input  wire [7:0] b,       // 8-bit input B
    input  wire [1:0] op,      // 2-bit operation selector (00, 01, 10, 11)
    output reg  [7:0] result   // 8-bit output
);

    // This block triggers instantly whenever ANY input changes
    always @(*) begin
        case (op)
            2'b00: result = a + b;   // Add
            2'b01: result = a - b;   // Subtract
            2'b10: result = a & b;   // Bitwise AND
            2'b11: result = a | b;   // Bitwise OR
            default: result = 8'b0;  // Fallback
        endcase
    end

endmodule
