// End-to-end smoke test for the reflex game: boots the full pochoco_soc
// with sw/game_smoke_test.hex (a copy of game.s with its 3s/decisec
// constants swapped for tiny cycle counts -- see that file's header) so a
// complete 10-round game finishes in a few thousand simulated cycles
// instead of ~750 million. It watches o_LED to find out when a target LED
// lights up and reacts through i_Switch, so it doesn't need to know the
// pseudo-random sequence in advance.
//
// This does NOT validate the real 25 MHz timing in game.s (3s wait, decima
// conversion) or the real ~10ms debounce settle time in rtl/debouncer.v --
// those only come from hand-tracing their constants (documented in each
// file's own comments; the debounce settle time separately has its own
// bounce-simulated unit test in sim/tb_pochoco_periph.v). What this
// exercises is control flow through the full SoC + game.hex: round
// sequencing, the wrong-button retry (and that it preserves
// correct_count/sum_decimas), the 10-round loop, and the average/display
// packing. A `defparam` (see below) speeds up the debounce just for this
// simulation; pochoco_soc/game_top are otherwise instantiated exactly as
// they are for real hardware.
//
// Run:
//   iverilog -g2012 -o /tmp/tb_game_smoke.vvp sim/tb_game_smoke.v \
//     rtl/pochoco_soc.v rtl/pochoco_ram.v rtl/pochoco_periph.v \
//     rtl/pochoco_spi_slave.v rtl/debouncer.v rtl/espino_core/*.v \
//     /usr/share/yosys/ice40/cells_sim.v
//   vvp /tmp/tb_game_smoke.vvp
//
// (cells_sim.v provides a behavioral model for the SB_RAM40_4K primitives
// that espino_register_file.v instantiates directly -- without it iverilog
// can't elaborate the register file.)

`timescale 1ns/1ps

module tb_game_smoke;

  reg clk = 0;
  always #5 clk = ~clk;

  reg [3:0] switches = 4'b0000;
  wire [3:0] leds;

  // Instantiated exactly as game_top.v instantiates it for real hardware --
  // NumWords/MemFile are the only parameters pochoco_soc exposes, on
  // purpose, so production RTL doesn't need a testing-only knob threaded
  // through it. The real hardware debounce is ~10ms (2^18 cycles), which
  // would make every simulated button press take ~525,000 cycles to
  // settle (~50+ minutes wall-clock for a full 10-round game in iverilog --
  // measured, not estimated). Instead, `defparam` below reaches straight
  // into the u_periph instance buried inside dut and overrides its
  // DEBOUNCE_TICK_BITS just for this simulation, with zero changes to any
  // production .v file.
  pochoco_soc #(
    .NumWords (512),
    .MemFile  ("sw/game_smoke_test.hex")
  ) dut (
    .i_Clk      (clk),
    .o_LED      (leds),
    .i_Switch   (switches),
    .i_SPI_SCLK (1'b0),
    .i_SPI_MOSI (1'b0),
    .i_SPI_CS_n (1'b1)
  );

  defparam dut.u_periph.DEBOUNCE_TICK_BITS = 4;

  // Worst case for debounce_bank to register a new stable value: up to 2
  // full sample periods (2 * 2^TICK_BITS cycles) if the value changes right
  // after a sample point. Hold every simulated press for that long plus
  // margin. Must match the defparam override above.
  localparam PRESS_HOLD = 2 * (1 << 4) + 20;

  integer round_num = 0;
  integer guard = 60;
  integer errors = 0;
  reg tested_wrong = 0;
  reg [3:0] seen_pattern = 4'b0000;

  // Global watchdog so a real bug (e.g. an infinite wait) fails fast
  // instead of hanging the simulator.
  initial begin
    #2_000_000;
    $display("FAIL: watchdog timeout, simulation did not finish");
    errors = errors + 1;
    $display("%0d TEST(S) FAILED", errors);
    $finish;
  end

  initial begin
    wait (leds == 4'b1111);
    $display("PASS: phase 1 seen (all 4 LEDs on) at t=%0t", $time);

    while (round_num < 10 && guard > 0) begin
      wait (leds != 4'b1111 && leds != 4'b0000);
      repeat (5) @(posedge clk); // let the DUT clear its own wait_release check first

      if (!tested_wrong) begin
        tested_wrong = 1;
        if (leds == 4'b0001) switches = 4'b0010; else switches = 4'b0001;
        repeat (PRESS_HOLD) @(posedge clk);
        switches = 4'b0000;
        wait (leds == 4'b1111); // round must restart (back to the 4-LED phase)
        $display("PASS: wrong button triggered a round restart at t=%0t", $time);
      end else begin
        seen_pattern = seen_pattern | leds;
        switches = leds; // press exactly the lit target LED
        repeat (PRESS_HOLD) @(posedge clk);
        switches = 4'b0000;
        round_num = round_num + 1;
        if (round_num < 10) wait (leds == 4'b1111);
      end
      guard = guard - 1;
    end

    if (round_num != 10) begin
      $display("FAIL: only completed %0d/10 correct rounds (guard ran out)", round_num);
      errors = errors + 1;
    end else begin
      $display("PASS: completed 10 correct rounds");
    end

    if (seen_pattern == 4'b0001 || seen_pattern == 4'b0010 ||
        seen_pattern == 4'b0100 || seen_pattern == 4'b1000 || seen_pattern == 4'b0000) begin
      $display("FAIL: same LED targeted on every round (pattern=%b), not perceptibly random", seen_pattern);
      errors = errors + 1;
    end else begin
      $display("PASS: at least two different target LEDs seen across rounds (pattern=%b)", seen_pattern);
    end

    // After the 10th correct round the program should halt (jal x0, halt)
    // showing the average, not loop back to the 4-LED phase again.
    repeat (300) @(posedge clk);
    if (leds == 4'b1111) begin
      $display("FAIL: LEDs cycled back to phase 1 after round 10 (game kept looping)");
      errors = errors + 1;
    end else begin
      $display("PASS: game halted after round 10, LEDs = %b", leds);
    end

    $display("Final digit_q (average, packed decenas*16+unidades) = 0x%02h", dut.u_periph.digit_q);
    if (dut.u_periph.digit_q[7:4] <= 4'd9 && dut.u_periph.digit_q[3:0] <= 4'd9) begin
      $display("PASS: average digit_q nibbles are valid decimal digits (0-9 each)");
    end else begin
      $display("FAIL: average digit_q nibbles are not valid decimal digits: 0x%02h", dut.u_periph.digit_q);
      errors = errors + 1;
    end

    if (errors == 0) $display("ALL TESTS PASSED");
    else $display("%0d TEST(S) FAILED", errors);
    $finish;
  end

endmodule
