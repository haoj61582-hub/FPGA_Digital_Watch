// Seven - segment display decoder for hexadecimal digits .
//
// Parameters :
// ACTIVE_LOW - 1 for active - low LEDs ( for example , DE1 - SoC), 0 for active - high .
//
// Ports :
// digit [3:0] - Hexadecimal digit to display (0 x0 to 0xF).
// blank - When high , all segments are turned off.
// segments [6:0] - Segment outputs [g,f,e,d,c,b,a]


`timescale 1ns / 1ps

// Seven-segment display decoder for hexadecimal digits.
module seven_segment #(
    parameter int ACTIVE_LOW = 1
) (
    input logic [3:0] digit,
    input logic blank,
    output logic [6:0] segments
);

  logic [6:0]segments_active_high;

  always_comb begin
    if (blank) begin
      segments_active_high = 7'b0000000;
    end else begin
      unique case (digit)
        4'h0: segments_active_high = 7'b0111111;
        4'h1: segments_active_high = 7'b0000110;
        4'h2: segments_active_high = 7'b1011011;
        4'h3: segments_active_high = 7'b1001111;
        4'h4: segments_active_high = 7'b1100110;
        4'h5: segments_active_high = 7'b1101101;
        4'h6: segments_active_high = 7'b1111101;
        4'h7: segments_active_high = 7'b0000111;
        4'h8: segments_active_high = 7'b1111111;
        4'h9: segments_active_high = 7'b1101111;
        4'hA: segments_active_high = 7'b1110111;
        4'hB: segments_active_high = 7'b1111100;
        4'hC: segments_active_high = 7'b0111001;
        4'hD: segments_active_high = 7'b1011110;
        4'hE: segments_active_high = 7'b1111001;
        4'hF: segments_active_high = 7'b1110001;
      endcase
    end
  end

  assign segments = (ACTIVE_LOW != 0) ? ~segments_active_high : segments_active_high;

endmodule
