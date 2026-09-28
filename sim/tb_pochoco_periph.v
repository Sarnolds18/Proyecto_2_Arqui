// Self-checking testbench for pochoco_periph, focused on the new cycle
// counter at offset 0x0C (off==3): free-running from reset, and
// resettable to any value with a write. Also re-checks LEDs/digit/buttons
// (including the debounce path, with a bounce simulated) so the counter
// and debouncer additions didn't break the existing offsets.
// DEBOUNCE_TICK_BITS is overridden small here purely to simulate fast; real
// hardware uses the default 18 (~10ms at 25MHz, see rtl/debouncer.v).
//
// Run: iverilog -o /tmp/tb_periph.vvp sim/tb_pochoco_periph.v rtl/pochoco_periph.v
//      vvp /tmp/tb_periph.vvp

`timescale 1ns/1ps

module tb_pochoco_periph;

  reg        clk_i = 0;
  reg        rst_ni = 0;
  reg        sel_i = 0;
  reg        req_i = 0;
  reg        we_i = 0;
  reg [7:0]  addr_i = 8'b0;
  reg [31:0] wdata_i = 32'b0;
  wire [31:0] rdata_o;
  wire [3:0]  leds_o;
  reg  [3:0]  btn_i = 4'b0;
  wire [6:0]  seg1_o, seg2_o;

  integer errors = 0;

  pochoco_periph #(.DEBOUNCE_TICK_BITS(4)) dut (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),
    .sel_i   (sel_i),
    .req_i   (req_i),
    .we_i    (we_i),
    .addr_i  (addr_i),
    .wdata_i (wdata_i),
    .rdata_o (rdata_o),
    .leds_o  (leds_o),
    .btn_i   (btn_i),
    .seg1_o  (seg1_o),
    .seg2_o  (seg2_o)
  );

  always #5 clk_i = ~clk_i; // 100 MHz sim clock, unit-agnostic for this tb

  task check32(input [63*8-1:0] name, input [31:0] got, input [31:0] expected);
    begin
      if (got !== expected) begin
        $display("FAIL: %0s: got %0d (0x%08h), expected %0d (0x%08h)",
                  name, got, got, expected, expected);
        errors = errors + 1;
      end else begin
        $display("PASS: %0s = %0d", name, got);
      end
    end
  endtask

  task read_off(input [5:0] off, output [31:0] data);
    begin
      @(negedge clk_i);
      addr_i  = {off, 2'b00};
      sel_i   = 1'b1;
      req_i   = 1'b1;
      we_i    = 1'b0;
      @(negedge clk_i); // rdata_o is registered: valid one cycle after the request
      data    = rdata_o;
      sel_i   = 1'b0;
      req_i   = 1'b0;
    end
  endtask

  task write_off(input [5:0] off, input [31:0] data);
    begin
      @(negedge clk_i);
      addr_i  = {off, 2'b00};
      wdata_i = data;
      sel_i   = 1'b1;
      req_i   = 1'b1;
      we_i    = 1'b1;
      @(negedge clk_i);
      sel_i   = 1'b0;
      req_i   = 1'b0;
      we_i    = 1'b0;
    end
  endtask

  reg [31:0] cyc_a, cyc_b;
  integer i;

  initial begin
    // Reset
    rst_ni = 0;
    repeat (3) @(negedge clk_i);
    rst_ni = 1;

    // --- Cycle counter: free-running ---
    read_off(6'd3, cyc_a);
    repeat (10) @(negedge clk_i); // 10 idle cycles: counter must strictly advance,
                                  // and by roughly 10 (some slack for read_off's own
                                  // request/capture cycles around each read)
    read_off(6'd3, cyc_b);
    check32("cycle counter advances over 10 idle cycles",
            (cyc_b > cyc_a) && (cyc_b - cyc_a >= 32'd8) && (cyc_b - cyc_a <= 32'd16), 1'b1);

    // --- Cycle counter: resettable by write ---
    write_off(6'd3, 32'd0);
    read_off(6'd3, cyc_a);
    check32("cycle counter small right after reset-to-0 write", (cyc_a <= 32'd2), 1'b1);

    write_off(6'd3, 32'd1000);
    read_off(6'd3, cyc_a);
    check32("cycle counter reloads to written value (+ a couple cycles)",
            (cyc_a >= 32'd1000) && (cyc_a <= 32'd1003), 1'b1);

    // --- Existing offsets still work ---
    write_off(6'd1, 32'hF); // LEDs
    @(negedge clk_i);
    check32("leds_o reflects led register", {28'b0, leds_o}, 32'hF);

    write_off(6'd0, 32'hA5); // digit register (7-seg)
    @(negedge clk_i);
    // 0xA5 -> seg1 shows hex 'A' (0xE0>>... use known encoding), seg2 shows hex '5'
    check32("seg1_o decodes high nibble (0xA)", {25'b0, seg1_o}, {25'b0, 7'b1110111});
    check32("seg2_o decodes low nibble (0x5)",  {25'b0, seg2_o}, {25'b0, 7'b1101101});

    // Buttons now go through debounce_bank (DEBOUNCE_TICK_BITS=4 here for
    // speed -> samples every 2^4=16 cycles; 18 on real hardware -> ~10ms at
    // 25MHz). It only accepts a value once two consecutive slow samples
    // agree, so simulate a bouncy press, then hold the final value across
    // more than 2 sample periods before checking it settled.
    btn_i = 4'b0000;
    btn_i = 4'b1010; @(negedge clk_i);
    btn_i = 4'b0010; @(negedge clk_i);
    btn_i = 4'b1010; @(negedge clk_i);
    btn_i = 4'b0010; @(negedge clk_i);
    btn_i = 4'b1010; // settles here
    repeat (40) @(negedge clk_i); // > 2 sample periods, let it settle
    read_off(6'd2, cyc_a);
    check32("buttons readback settles after simulated bounce", cyc_a, 32'b1010);

    btn_i = 4'b0000;
    repeat (40) @(negedge clk_i);
    read_off(6'd2, cyc_a);
    check32("buttons readback follows release after debounce", cyc_a, 32'b0000);

    if (errors == 0) $display("ALL TESTS PASSED");
    else $display("%0d TEST(S) FAILED", errors);

    $finish;
  end

endmodule
