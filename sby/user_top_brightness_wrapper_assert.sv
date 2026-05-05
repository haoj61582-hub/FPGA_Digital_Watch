`timescale 1ns / 1ps

module user_top_brightness_wrapper_assert #(
    parameter int CYCLES_PER_SECOND = 8000
) (
    input logic clk,
    input logic [3:0] button,
    input logic [9:0] sw,
    output logic [9:0] led,
    output logic [6:0] hours_disp,
    output logic [6:0] minutes_disp,
    output logic [6:0] seconds_disp,
    output logic blank_hours,
    output logic blank_minutes,
    output logic blank_seconds
);

  user_top_brightness_wrapper #(
      .CYCLES_PER_SECOND(CYCLES_PER_SECOND)
  ) u_dut (
      .clk(clk),
      .button(button),
      .sw(sw),
      .led(led),
      .hours_disp(hours_disp),
      .minutes_disp(minutes_disp),
      .seconds_disp(seconds_disp),
      .blank_hours(blank_hours),
      .blank_minutes(blank_minutes),
      .blank_seconds(blank_seconds)
  );

  // verilog_lint: waive-start always-comb

  // Hide $initstate from verilator
  // `ifdef VERILATOR
  //   wire start = 0;
  // `else
  //   wire start = $initstate;
  // `endif

  // Ensure parameter values are sensible
  initial assert (CYCLES_PER_SECOND >= 1000);

  // If the underlying module asserts blank, it must be passed through
  always @(*) begin
    if (button[0]) a_blank_hours : assert (blank_hours);
    if (button[1]) a_blank_mins : assert (blank_minutes);
    if (button[2]) a_blank_secs : assert (blank_seconds);
  end

  // Full intensity means no additional blanking
  logic [1:0] brightness_sel;
  assign brightness_sel = sw[9:8];
  always @(*) begin
    if (blank_hours && brightness_sel == 2'b10) a_full_hours : assert (button[0]);
    if (blank_minutes && brightness_sel == 2'b10) a_full_mins : assert (button[1]);
    if (blank_seconds && brightness_sel == 2'b10) a_full_secs : assert (button[2]);
  end

  // Check switches are passed through
  wire [9:0] expected_led = clk ? sw : ~sw;
  always @(*) a_sw_passthrough : assert (led == expected_led);

  // Check other wiring
  always @(*)
    a_other :
    assert ((hours_disp == button[3] ? 7'd16 : 7'd7)
      && (minutes_disp == button[3] ? 7'd38 : 7'd23)
      && (seconds_disp == button[3] ? 7'd59 : 7'd45));

endmodule
