// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)

// Free-running 32-bit cycle counter (MMIO offset 0x0C in pochoco_periph).
// Increments every clock cycle from reset; load_i loads data_i instead
// (writing 0 zeroes it), so software can restart the count at the start of a
// round. Kept as its own module so it stays identifiable after synthesis and
// in the layout (instance u_cycle_counter).
module pochoco_cycle_counter (
  input  wire        clk_i,
  input  wire        rst_ni,
  input  wire        load_i,
  input  wire [31:0] data_i,
  output reg  [31:0] count_o
);

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni)     count_o <= 32'b0;
    else if (load_i) count_o <= data_i;
    else             count_o <= count_o + 32'd1;
  end

endmodule
