module top_time_display_v1 #(
parameter int CYCLES_PER_SECOND = 50 _000_000
) (
input logic CLOCK_50 ,

input logic [1:0] SW ,
output logic [6:0] HEX5 ,
output logic [6:0] HEX4 ,
output logic [6:0] HEX3 ,
output logic [6:0] HEX2 ,
output logic [6:0] HEX1 ,
output logic [6:0] HEX0
) ;

