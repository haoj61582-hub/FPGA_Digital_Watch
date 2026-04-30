`timescale 1ns / 1ps

module top_time_display_v1 #(
    parameter int CYCLES_PER_SECOND = 50_000_000
) (
    input logic CLOCK_50,
    input logic [1:0] SW,
    output logic [6:0] HEX5,
    output logic [6:0] HEX4,
    output logic [6:0] HEX3,
    output logic [6:0] HEX2,
    output logic [6:0] HEX1,
    output logic [6:0] HEX0
);

  localparam int CyclesPer25Hz = CYCLES_PER_SECOND / 25;
  localparam int CyclesPer1kHz = CYCLES_PER_SECOND / 1000;

  logic tick_1hz;
  logic tick_25hz;
  logic tick_1khz;
  logic tick_enable;

  logic [4:0] hours;
  logic [5:0] minutes;
  logic [5:0] seconds;

  logic [3:0] hours_tens;
  logic [3:0] hours_ones;
  logic [3:0] minutes_tens;
  logic [3:0] minutes_ones;
  logic [3:0] seconds_tens;
  logic [3:0] seconds_ones;

  restartable_rate_generator #(
      .CYCLE_COUNT(CYCLES_PER_SECOND)
  ) u_tick_1hz (
      .clk (CLOCK_50),
      .run (SW == 2'b00),
      .tick(tick_1hz)
  );

  restartable_rate_generator #(
      .CYCLE_COUNT(CyclesPer25Hz)
  ) u_tick_25hz (
      .clk (CLOCK_50),
      .run (SW == 2'b01),
      .tick(tick_25hz)
  );

  restartable_rate_generator #(
      .CYCLE_COUNT(CyclesPer1kHz)
  ) u_tick_1khz (
      .clk (CLOCK_50),
      .run (SW == 2'b10),
      .tick(tick_1khz)
  );

  assign tick_enable = (SW == 2'b00) ? tick_1hz :
                       (SW == 2'b01) ? tick_25hz :
                       (SW == 2'b10) ? tick_1khz :
                                       1'b1;

  hms_counter u_hms_counter (
      .clk    (CLOCK_50),
      .enable (tick_enable),
      .hours  (hours),
      .minutes(minutes),
      .seconds(seconds)
  );

  binary_to_bcd u_hours_bcd (
      .bin ({2'b00, hours}),
      .tens(hours_tens),
      .ones(hours_ones)
  );

  binary_to_bcd u_minutes_bcd (
      .bin ({1'b0, minutes}),
      .tens(minutes_tens),
      .ones(minutes_ones)
  );

  binary_to_bcd u_seconds_bcd (
      .bin ({1'b0, seconds}),
      .tens(seconds_tens),
      .ones(seconds_ones)
  );

  seven_segment u_HEX5 (
      .digit   (hours_tens),
      .blank   (1'b0),
      .segments(HEX5)
  );

  seven_segment u_HEX4 (
      .digit   (hours_ones),
      .blank   (1'b0),
      .segments(HEX4)
  );

  seven_segment u_HEX3 (
      .digit   (minutes_tens),
      .blank   (1'b0),
      .segments(HEX3)
  );

  seven_segment u_HEX2 (
      .digit   (minutes_ones),
      .blank   (1'b0),
      .segments(HEX2)
  );

  seven_segment u_HEX1 (
      .digit   (seconds_tens),
      .blank   (1'b0),
      .segments(HEX1)
  );

  seven_segment u_HEX0 (
      .digit   (seconds_ones),
      .blank   (1'b0),
      .segments(HEX0)
  );

endmodule
