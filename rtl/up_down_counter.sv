`timescale 1ns / 1ps

module up_down_counter #(
    parameter int MAX = 2,
    parameter int WIDTH = 2
) (
    input logic clk,
    input logic enable,
    input logic up,
    output logic [WIDTH-1:0] count
);

  localparam logic [WIDTH-1:0] Max = WIDTH'(MAX);
  localparam logic [WIDTH-1:0] One = WIDTH'(1);

  logic [WIDTH-1:0] next_count;

  initial count = '0;

  always_comb begin
    if (up) begin
      next_count = (count == Max) ? '0 : count + One;
    end else begin
      next_count = (count == '0) ? Max : count - One;
    end
  end

  always_ff @(posedge clk) begin
    if (enable) begin
      count <= next_count;
    end
  end

endmodule

