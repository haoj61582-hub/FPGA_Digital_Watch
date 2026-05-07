`timescale 1ns / 1ps

module editable_counter #(
    parameter int N = 60,
    parameter int WIDTH = 6
) (
    input logic clk,
    input logic tick,
    input logic edit_mode,  //when high, inc and dec inputs are active. when low, the counter is incremented by tick events
    input logic inc,  //inc and dec are only active when edit_mode is high. If both are high, inc takes precedence
    input logic dec,  //inc and dec are only active when edit_mode is high. If both are high, inc takes precedence
    output logic [WIDTH-1:0] count
);

  logic enable;
  logic up;

  up_down_counter #(
      .MAX  (N - 1),
      .WIDTH(WIDTH)
  ) u_counter (
      .clk   (clk),
      .enable(enable),
      .up    (up),
      .count (count)
  );

  wire inc_event = edit_mode && inc && !dec;
  wire dec_event = edit_mode && dec && !inc;
  wire tick_event = !edit_mode && tick;

  assign up = inc_event || tick_event;
  assign enable = inc_event || dec_event || tick_event;

endmodule
