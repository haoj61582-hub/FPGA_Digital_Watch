// ------------------------------------------------------------------
// Board wrapper for the DE1-SoC.
//
// This module handles all board-specific concerns:
//   - Synchronises the KEY inputs and converts them to active-high.
//   - Drives the HEX displays from decimal values.
//   - Sets CYCLES_PER_SECOND to the DE1-SoC clock frequency
//     (50 MHz).
//
// To load a different design, instantiate it in place of user_top
// below.
// ------------------------------------------------------------------
`timescale 1ns / 1ps

module top_de1_soc (
    input logic CLOCK_50,
    input logic [3:0] KEY,  // active-low, asynchronous
    input logic [9:0] SW,
    output logic [9:0] LEDR,
    output logic [6:0] HEX0,
    output logic [6:0] HEX1,
    output logic [6:0] HEX2,
    output logic [6:0] HEX3,
    output logic [6:0] HEX4,
    output logic [6:0] HEX5
);

  logic [3:0] button;

  key_synchroniser u_key_synchroniser (
      .clk     (CLOCK_50),
      .key_n   (KEY),
      .key_sync(button)
  );

  logic [6:0] hours, minutes, seconds;
  logic blank_hours, blank_minutes, blank_seconds;

  // Replace user_top with your user top-level module
  user_top #(
      .CYCLES_PER_SECOND(50_000_000)
  ) u_user_top (
      .clk          (CLOCK_50),
      .button       (button),
      .sw           (SW),
      .led          (LEDR),
      .hours_disp   (hours),
      .minutes_disp (minutes),
      .seconds_disp (seconds),
      .blank_hours  (blank_hours),
      .blank_minutes(blank_minutes),
      .blank_seconds(blank_seconds)
  );

  decimal_display_driver u_decimal_display_driver (
      .value0(seconds),
      .value1(minutes),
      .value2(hours),
      .blank0(blank_seconds),
      .blank1(blank_minutes),
      .blank2(blank_hours),
      .HEX0  (HEX0),
      .HEX1  (HEX1),
      .HEX2  (HEX2),
      .HEX3  (HEX3),
      .HEX4  (HEX4),
      .HEX5  (HEX5)
  );

endmodule
