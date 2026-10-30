// Self-checking testbench for espino_register_file (flip-flop version).
// Checks: every register reads 0 after reset, x0 ignores writes, synchronous
// read (data appears one edge after the address), read-before-write on a
// same-cycle read/write, both ports independent, and a random write/read
// sequence against a reference array kept in the testbench.
//
// Run: iverilog -g2012 -o /tmp/tb_rf.vvp sim/tb_register_file.v \
//        rtl/espino_core/espino_register_file.v
//      vvp /tmp/tb_rf.vvp

`timescale 1ns/1ps

module tb_register_file;

  reg         clk_i = 0;
  reg         rst_ni = 0;
  reg  [3:0]  raddr_a_i = 0, raddr_b_i = 0, waddr_i = 0;
  reg  [31:0] wdata_i = 0;
  reg         we_i = 0;
  wire [31:0] rdata_a_o, rdata_b_o;

  integer errors = 0;
  integer i, k;
  reg [31:0] ref_q [0:15];
  reg [31:0] exp_a, exp_b;

  espino_register_file dut (
    .clk_i     (clk_i),
    .rst_ni    (rst_ni),
    .raddr_a_i (raddr_a_i),
    .rdata_a_o (rdata_a_o),
    .raddr_b_i (raddr_b_i),
    .rdata_b_o (rdata_b_o),
    .waddr_i   (waddr_i),
    .wdata_i   (wdata_i),
    .we_i      (we_i)
  );

  always #5 clk_i = ~clk_i;

  task check(input [31:0] got, input [31:0] exp, input [127:0] what);
    if (got !== exp) begin
      $display("FAIL: %0s got %h expected %h at t=%0t", what, got, exp, $time);
      errors = errors + 1;
    end
  endtask

  // Drive inputs after the falling edge, sample after the next rising edge.
  task cycle;
    begin
      @(posedge clk_i); #1;
    end
  endtask

  initial begin
    for (i = 0; i < 16; i = i + 1) ref_q[i] = 32'b0;

    #12 rst_ni = 1;
    @(negedge clk_i);

    // 1. All registers read 0 after reset.
    for (i = 0; i < 16; i = i + 1) begin
      raddr_a_i = i; raddr_b_i = 15 - i;
      cycle;
      check(rdata_a_o, 32'b0, "reset port A");
      check(rdata_b_o, 32'b0, "reset port B");
    end

    // 2. Write to x0 is ignored.
    @(negedge clk_i);
    we_i = 1; waddr_i = 0; wdata_i = 32'hDEAD_BEEF;
    cycle; we_i = 0;
    raddr_a_i = 0; cycle;
    check(rdata_a_o, 32'b0, "x0 after write");

    // 3. Synchronous read: changing the address does not change rdata until
    //    the next rising edge.
    @(negedge clk_i);
    we_i = 1; waddr_i = 5; wdata_i = 32'h1234_5678;
    cycle; we_i = 0;
    @(negedge clk_i);
    raddr_a_i = 5; #1;
    check(rdata_a_o, 32'b0, "sync read before edge");
    cycle;
    check(rdata_a_o, 32'h1234_5678, "sync read after edge");

    // 4. Read-before-write: same-cycle read and write of x5 returns the old
    //    value; the new one shows up on the following read edge.
    @(negedge clk_i);
    raddr_b_i = 5; we_i = 1; waddr_i = 5; wdata_i = 32'hCAFE_0001;
    cycle; we_i = 0;
    check(rdata_b_o, 32'h1234_5678, "read-before-write");
    cycle;
    check(rdata_b_o, 32'hCAFE_0001, "value after write");
    ref_q[5] = 32'hCAFE_0001;

    // 5. Random writes/reads on both ports against the reference array.
    for (k = 0; k < 2000; k = k + 1) begin
      @(negedge clk_i);
      raddr_a_i = $random; raddr_b_i = $random;
      we_i = $random; waddr_i = $random; wdata_i = $random;
      exp_a = ref_q[raddr_a_i];
      exp_b = ref_q[raddr_b_i];
      if (we_i && waddr_i != 0) ref_q[waddr_i] = wdata_i;
      cycle;
      check(rdata_a_o, exp_a, "random port A");
      check(rdata_b_o, exp_b, "random port B");
    end

    if (errors == 0) $display("ALL TESTS PASSED");
    else             $display("%0d ERRORS", errors);
    $finish;
  end

endmodule
