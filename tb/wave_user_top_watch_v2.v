`timescale 1ns/1ps
module wave_user_top_watch_v2;
  reg        clk    = 0;
  reg  [3:0] button = 4'b0;
  reg  [9:0] sw     = 10'b0;
  wire [9:0] led;
  wire [6:0] hours_disp;
  wire [6:0] minutes_disp;
  wire [6:0] seconds_disp;
  wire       blank_hours;
  wire       blank_minutes;
  wire       blank_seconds;

  // CYCLES_PER_SECOND=50 keeps the simulation concise:
  //   1 simulated second  = 50 cycles  = 500 ns
  //   PWM period (0.5 s)  = 25 cycles  = 250 ns  (2 Hz flash)
  //   PWM high (0.1 s)    =  5 cycles  =  50 ns  (display off, 20% of period)
  //   Hold threshold (1s) = 50 cycles  = 500 ns
  user_top_watch_v2 #(
      .CYCLES_PER_SECOND(50)
  ) dut (
      .clk         (clk),
      .button      (button),
      .sw          (sw),
      .led         (led),
      .hours_disp  (hours_disp),
      .minutes_disp(minutes_disp),
      .seconds_disp(seconds_disp),
      .blank_hours  (blank_hours),
      .blank_minutes(blank_minutes),
      .blank_seconds(blank_seconds)
  );

  always #5 clk = ~clk;  // 100 MHz: 10 ns period

  initial begin
    $dumpfile("wave_user_top_watch_v2.vcd");
    $dumpvars(0, wave_user_top_watch_v2);

    // --- Normal operation: watch counts for ~1.5 seconds ---
    // seconds_disp advances once per 50 cycles; blank_* remain 0.
    #750;  // 75 cycles = 1.5 simulated seconds

    // --- Long press: hold KEY[3] for 55 cycles (> HOLD_CYCLES=50) ---
    // button_hold_pulse fires at cycle 50 of the press, arming the latch.
    // mode_enable becomes 3'b001 (seconds selected); blank_seconds begins
    // pulsing at 2 Hz.  The rising edge at press start is ignored because
    // the latch is not yet armed.
    button[3] = 1;
    #550;  // 55 cycles held high

    button[3] = 0;
    #1000;  // 100 cycles released; observe seconds flashing (4 PWM cycles visible)

    // --- Short press 1: advance seconds -> minutes ---
    // Rising edge detected while armed; mod-3 counter advances to 1.
    // mode_enable becomes 3'b010; blank_minutes flashes, blank_seconds stops.
    button[3] = 1;
    #100;  // 10 cycles
    button[3] = 0;
    #1000;  // 100 cycles released; observe minutes flashing (4 PWM cycles visible)

    // --- Short press 2: advance minutes -> hours ---
    // Counter advances to 2; mode_enable becomes 3'b100.
    button[3] = 1;
    #100;
    button[3] = 0;
    #1000;  // 100 cycles released; observe hours flashing (4 PWM cycles visible)

    // --- Short press 3: exit edit mode ---
    // disarm condition fires (count==2 && enable_counter); latch clears.
    // mode_enable returns to 3'b000; all blank_* return to 0.
    button[3] = 1;
    #100;
    button[3] = 0;

    // --- Normal operation resumes ---
    // blank_* are all 0; seconds_disp continues incrementing.
    #500;  // 50 cycles

    $finish;
  end
endmodule
