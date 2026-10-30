// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
//
// Authors:
// - Nicolás Villegas <navillegas@miuandes.cl>
//
// Flip-flop register file for ASIC (replaces the two SB_RAM40_4K pairs of the
// iCE40 version). x1..x15 are 32-bit flops; x0 is not stored and reads as 0.
// Keeps the timing the core expects from the old block RAM: read is
// synchronous (rdata_*_o is registered, valid one cycle after raddr_*_i, see
// ops_valid_q in espino_id_stage.v) and a write is visible from the next
// read edge on. rst_ni clears every register, matching INIT_0 = 0 of the
// block RAMs, so software sees the same initial state as on the FPGA.

module espino_register_file (
  input  wire        clk_i,
  input  wire        rst_ni,
  input  wire [3:0]  raddr_a_i,
  output reg  [31:0] rdata_a_o,
  input  wire [3:0]  raddr_b_i,
  output reg  [31:0] rdata_b_o,
  input  wire [3:0]  waddr_i,
  input  wire [31:0] wdata_i,
  input  wire        we_i
);
  reg [31:0] regs_q [1:15];

  integer i;
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      for (i = 1; i < 16; i = i + 1) regs_q[i] <= 32'b0;
    end else if (we_i && (waddr_i != 4'd0)) begin
      regs_q[waddr_i] <= wdata_i;
    end
  end

  // Read-before-write on a same-cycle read/write of the same register, as in
  // SB_RAM40_4K. The core never consumes that value: the write happens on
  // the commit cycle and the next instruction re-reads one cycle later.
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      rdata_a_o <= 32'b0;
      rdata_b_o <= 32'b0;
    end else begin
      rdata_a_o <= (raddr_a_i == 4'd0) ? 32'b0 : regs_q[raddr_a_i];
      rdata_b_o <= (raddr_b_i == 4'd0) ? 32'b0 : regs_q[raddr_b_i];
    end
  end
endmodule
