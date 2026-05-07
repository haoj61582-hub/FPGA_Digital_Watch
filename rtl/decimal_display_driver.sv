// ------------------------------------------------------------------
// decimal_display_driver
// ------------------------------------------------------------------
// Board-specific display driver for the DE1-SoC HEX displays.
//
// This module presents three decimal values (0-99) on the six
// seven-segment HEX displays (HEX5..HEX0).
// Each value uses two digits.
//
// The module accepts numeric values and blanking controls.
// Internally, it handles:
//   - binary-to-BCD conversion
//   - seven-segment decoding
//   - digit blanking
//   - active-low segment polarity
// ------------------------------------------------------------------
`timescale 1ns / 1ps

module decimal_display_driver (
    // Decimal values to be displayed (range: 0-99)
    // value0 -> HEX1 (tens) and HEX0 (ones)
    // value1 -> HEX3 (tens) and HEX2 (ones)
    // value2 -> HEX5 (tens) and HEX4 (ones)
    input logic [6:0] value0,
    input logic [6:0] value1,
    input logic [6:0] value2,

    // Blanking controls for each decimal value.
    // When asserted, both digits of the value are blanked.
    input logic blank0,
    input logic blank1,
    input logic blank2,

    // DE1-SoC seven-segment display outputs.
    // Active-low segments: [g,f,e,d,c,b,a]
    output logic [6:0] HEX0,
    output logic [6:0] HEX1,
    output logic [6:0] HEX2,
    output logic [6:0] HEX3,
    output logic [6:0] HEX4,
    output logic [6:0] HEX5
);

  // Pack scalar ports into arrays for use in the generate loop.
  // value_a[i] drives HEX(2i+1) (tens) and HEX(2i) (ones).
  logic [6:0] value_a[3];
  assign value_a[0] = value0;
  assign value_a[1] = value1;
  assign value_a[2] = value2;

  logic blank_a[3];
  assign blank_a[0] = blank0;
  assign blank_a[1] = blank1;
  assign blank_a[2] = blank2;

  logic [6:0] hex_a[6];
  assign HEX0 = hex_a[0];
  assign HEX1 = hex_a[1];
  assign HEX2 = hex_a[2];
  assign HEX3 = hex_a[3];
  assign HEX4 = hex_a[4];
  assign HEX5 = hex_a[5];

  genvar i;
  generate
    for (i = 0; i < 3; i = i + 1) begin : g_digit_pair
      logic [3:0] tens;
      logic [3:0] ones;

      binary_to_bcd u_binary_to_bcd (
          .bin (value_a[i]),
          .tens(tens),
          .ones(ones)
      );

      seven_segment #(
          .ACTIVE_LOW(1)
      ) u_ones (
          .digit   (ones),
          .blank   (blank_a[i]),
          .segments(hex_a[2 * i])
      );

      seven_segment #(
          .ACTIVE_LOW(1)
      ) u_tens (
          .digit   (tens),
          .blank   (blank_a[i]),
          .segments(hex_a[(2 * i) + 1])
      );
    end
  endgenerate

endmodule
