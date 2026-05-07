`timescale 1ns / 1ps

module arming_latch (
    input  logic clk,
    input  logic arm,
    input  logic disarm,
    output logic armed
);

  initial armed = 1'b0;

  always_ff @(posedge clk) begin
    if (disarm) begin
      armed <= 1'b0;
    end else if (arm) begin
      armed <= 1'b1;
    end
  end

endmodule
