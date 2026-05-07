`timescale 1ns / 1ps

module edit_mode_selector #(
    parameter int HOLD_CYCLES = 50_000_000
) (
    input logic clk,
    input logic button,
    output logic [2:0] mode_enable
);

  logic long_press;
  logic press;
  logic armed;
  logic disarm;
  logic reset_counter;
  logic enable_counter;
  logic [1:0] count;

  button_hold_pulse #(
      .HOLD_CYCLES(HOLD_CYCLES)
  ) u_hold_pulse (
      .clk   (clk),
      .button(button),
      .pulse (long_press)
  );

  rising_edge_detector u_detector (
      .clk   (clk),
      .sig_in(button),
      .rise  (press)
  );

  arming_latch u_latch (
      .clk   (clk),
      .arm   (long_press),
      .disarm(disarm),
      .armed (armed)
  );

  mod_n_counter #(
      .N    (3),
      .WIDTH(2)
  ) u_mod_3_counter (
      .clk   (clk),
      .rst   (reset_counter),
      .enable(enable_counter),
      .count (count)
  );

  assign enable_counter = armed && press;
  assign reset_counter = !armed;
  assign disarm = enable_counter && (count == 2'd2);
  assign mode_enable = armed ? (3'b001 << count) : 3'b000;

endmodule
