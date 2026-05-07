`timescale 1ns / 1ps

module key_synchroniser (
    input logic clk,  //clock signal for synchronisation
    input logic [3:0] key_n,  //active low key inputs
    output logic [3:0] key_sync  //synchronised key outputs
);

  logic [3:0] key_meta;  //intermediate register for metastability resolution
  logic [3:0] key_sync_r;  //register for synchronised key outputs

  initial key_meta = 4'b0000;
  initial key_sync_r = 4'b0000;

  assign key_sync = key_sync_r;

  always_ff @(posedge clk) begin
    key_meta   <= ~key_n;
    key_sync_r <= key_meta;
  end

endmodule
