// Self-checking testbench for espino_load_store_unit.
// Emulates what the core does on a load: the request stays up (same addr,
// type and sign) while busy_o stalls the core for one cycle, the memory
// answers one edge later (synchronous read, like pochoco_mem_rom/ff), and
// rdata_o is checked in that second cycle, when the core writes it back.
// Covers lb/lbu/lh/lhu/lw at every legal byte offset of several words
// (bytes with and without the sign bit), back-to-back loads with different
// offsets, and store byte enables/data. Expected values come from a
// reference model in this file (shift + mask + sign extension), not from
// the RTL.
//
// Run: iverilog -g2012 -o /tmp/tb_lsu.vvp sim/tb_load_store_unit.v \
//        rtl/espino_core/espino_load_store_unit.v
//      vvp /tmp/tb_lsu.vvp

`timescale 1ns/1ps

module tb_load_store_unit;

  localparam [1:0] BYTE = 2'd0, HALF = 2'd1, WORD = 2'd2;

  reg         clk_i = 0;
  reg         rst_ni = 0;
  reg         req_i = 0;
  reg         we_i = 0;
  reg  [1:0]  type_i = WORD;
  reg         sign_i = 0;
  reg  [31:0] addr_i = 0;
  reg  [31:0] wdata_i = 0;
  wire [31:0] rdata_o;
  wire        busy_o;
  wire        data_req_o, data_we_o;
  wire [3:0]  data_be_o;
  wire [31:0] data_addr_o, data_wdata_o;
  reg  [31:0] data_rdata_i = 0;

  integer errors = 0;
  integer checks = 0;
  integer w, off, s;

  reg [31:0] mem [0:3];
  initial begin
    mem[0] = 32'h8F7A_E501;
    mem[1] = 32'h12F4_7F80;
    mem[2] = 32'hFFFF_FFFF;
    mem[3] = 32'h0080_8000;
  end

  espino_load_store_unit dut (
    .clk_i        (clk_i),
    .rst_ni       (rst_ni),
    .req_i        (req_i),
    .we_i         (we_i),
    .type_i       (type_i),
    .sign_i       (sign_i),
    .addr_i       (addr_i),
    .wdata_i      (wdata_i),
    .rdata_o      (rdata_o),
    .busy_o       (busy_o),
    .data_req_o   (data_req_o),
    .data_we_o    (data_we_o),
    .data_be_o    (data_be_o),
    .data_addr_o  (data_addr_o),
    .data_wdata_o (data_wdata_o),
    .data_rdata_i (data_rdata_i)
  );

  always #5 clk_i = ~clk_i;

  // Synchronous-read memory: answers one edge after the request.
  always @(posedge clk_i)
    if (data_req_o && !data_we_o) data_rdata_i <= mem[data_addr_o[3:2]];

  // Reference model of a RISC-V load.
  function [31:0] ref_load(input [31:0] word, input [1:0] off,
                           input [1:0] typ, input sgn);
    reg [31:0] sh;
    begin
      sh = word >> (8 * off);
      case (typ)
        BYTE:    ref_load = sgn ? {{24{sh[7]}},  sh[7:0]}  : {24'b0, sh[7:0]};
        HALF:    ref_load = sgn ? {{16{sh[15]}}, sh[15:0]} : {16'b0, sh[15:0]};
        default: ref_load = word;
      endcase
    end
  endfunction

  task check(input [8*24-1:0] name, input [31:0] got, input [31:0] expected);
    begin
      checks = checks + 1;
      if (got !== expected) begin
        $display("FAIL: %0s: got 0x%08h, expected 0x%08h", name, got, expected);
        errors = errors + 1;
      end
    end
  endtask

  // One load, as the core issues it. Returns after the write-back cycle.
  task load(input integer word, input [1:0] off, input [1:0] typ, input sgn);
    begin
      @(negedge clk_i);
      req_i  = 1'b1;
      we_i   = 1'b0;
      type_i = typ;
      sign_i = sgn;
      addr_i = {26'b0, word[1:0], off};
      #1;
      check("busy in first cycle", {31'b0, busy_o}, 32'd1);
      @(negedge clk_i);         // second cycle: data is back, core commits
      check("busy in second cycle", {31'b0, busy_o}, 32'd0);
      check("load data", rdata_o, ref_load(mem[word], off, typ, sgn));
      @(negedge clk_i);
      req_i = 1'b0;
    end
  endtask

  initial begin
    repeat (2) @(negedge clk_i);
    rst_ni = 1'b1;

    // Every word, every legal offset, every load type.
    for (w = 0; w < 4; w = w + 1) begin
      for (off = 0; off < 4; off = off + 1)
        for (s = 0; s < 2; s = s + 1)
          load(w, off[1:0], BYTE, s[0]);
      for (off = 0; off < 4; off = off + 2)
        for (s = 0; s < 2; s = s + 1)
          load(w, off[1:0], HALF, s[0]);
      load(w, 2'd0, WORD, 1'b0);
    end

    // Back-to-back loads with no idle cycle in between, changing offset.
    @(negedge clk_i);
    req_i = 1'b1; we_i = 1'b0; type_i = BYTE; sign_i = 1'b1;
    addr_i = 32'h0000_0003;                       // mem[0] byte 3 = 0x8F
    @(negedge clk_i);
    check("b2b load 1", rdata_o, 32'hFFFF_FF8F);
    @(negedge clk_i);                             // next load right away
    type_i = HALF; sign_i = 1'b0; addr_i = 32'h0000_0006;  // mem[1] half 1
    @(negedge clk_i);
    check("b2b load 2", rdata_o, 32'h0000_12F4);
    @(negedge clk_i);
    req_i = 1'b0;

    // Stores: byte enables and replicated data (single cycle, no busy).
    @(negedge clk_i);
    req_i = 1'b1; we_i = 1'b1; wdata_i = 32'hA1B2_C3D4;
    for (off = 0; off < 4; off = off + 1) begin
      type_i = BYTE; addr_i = {30'b0, off[1:0]};
      #1;
      check("sb be", {28'b0, data_be_o}, 32'd1 << off);
      check("sb data", data_wdata_o, 32'hD4D4_D4D4);
      check("sb busy", {31'b0, busy_o}, 32'd0);
    end
    type_i = HALF; addr_i = 32'h2; #1;
    check("sh be", {28'b0, data_be_o}, 32'b1100);
    check("sh data", data_wdata_o, 32'hC3D4_C3D4);
    type_i = WORD; addr_i = 32'h0; #1;
    check("sw be", {28'b0, data_be_o}, 32'b1111);
    check("sw data", data_wdata_o, 32'hA1B2_C3D4);
    @(negedge clk_i);
    req_i = 1'b0; we_i = 1'b0;

    if (errors == 0) $display("ALL TESTS PASSED (%0d checks)", checks);
    else             $display("%0d of %0d CHECKS FAILED", errors, checks);
    $finish;
  end

endmodule
