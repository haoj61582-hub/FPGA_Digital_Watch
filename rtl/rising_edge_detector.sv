`timescale 1ns / 1ps

module rising_edge_detector (
    input  logic clk,
    input  logic sig_in,
    output logic rise
);

  logic sig_d;

  initial sig_d = 1'b0;

  always_ff @(posedge clk) begin
    sig_d <= sig_in;
  end

  assign rise = sig_in && !sig_d;

endmodule
