// This demo highlights the difference between Verilog simulation and
// SystemVerilog simulation.
//
// SystemVerilog simulators changed how they handle always @(*) blocks
// at initialization time: they are no longer run automatically. Therefore,
// the following code behaves differently under a SystemVerilog simulator.
// Change always @(*) to always_comb to recover the intended behaviour.
//
// To use Verilog:
//
//  iverilog -Wall demos/simulation.v
//  ./a.out
//
// OR to use SystemVerilog:
//
// iverilog -Wall -g2012 demos/simulation.v
// ./a.out
//

module simulation;
  reg clk = 0;
  reg go = 0;
  initial forever #5 clk = ~clk;

  wire out;
  circuit u_circuit (
      .clk(clk),
      .go (go),
      .out(out)
  );

  initial begin
    #20;  // Wait 2 clock cycles
    go = 1;
    #20;  // Wait 2 clock cycles
    $finish;
  end

  initial $monitor($realtime,, go,, out);

  initial begin
    $dumpfile("simulation.vcd");
    $dumpvars;
  end
endmodule

module circuit (
    input  clk,
    input  go,
    output out
);

  reg state = 1'b0;
  reg next_state;

  always @(posedge clk) state <= go ? next_state : 1'b0;

  always @(*) begin  // verilog_lint: waive always-comb
    next_state = !state;
  end

  assign out = state;
endmodule
