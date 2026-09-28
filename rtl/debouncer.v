// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
// Proyecto 2 - Juego de reflejos
//
// Debounce for the 4 buttons/switches, sharing a single slow "tick"
// generator instead of one magnitude-comparator counter per button (like
// proyecto1/src/debouncer.v). That per-button design was tried first and
// ported straight from Proyecto 1 (already proven on this same Go Board),
// but 4 instances pushed synthesis from 1225/1280 (95%) to 1444/1280 (112%)
// ICESTORM_LC on the iCE40 HX1K -- the espino_core + SoC already leave very
// little headroom, unlike Proyecto 1's small 4-bit calculator. This design
// keeps the same ~10 ms settle time but costs a fraction of the LUTs: one
// free-running TICK_BITS-wide counter's own MSB toggling is used directly
// as the slow sample enable (no comparator at all), and the 4 buttons are
// accepted together with a single 4-bit equality check between two
// consecutive slow samples instead of 4 independent per-bit comparators.
//
// At 25 MHz, TICK_BITS=18 samples roughly every 2^18 cycles = ~10.5 ms,
// matching Proyecto 1's proven 250,000-cycle (~10 ms) debounce window.
// Physical switch bounce settles in well under that (typically <5 ms), so
// two consecutive 10 ms-spaced samples agreeing is a reliable stability
// check, even though it samples periodically instead of continuously.

module debounce_bank #(
    parameter TICK_BITS = 18
) (
    input  wire       clk,
    input  wire [3:0] btn_i,
    output reg  [3:0] btn_estable
);

reg [TICK_BITS-1:0] tick_cnt;
reg                 tick_bit_prev;
reg [3:0]           btn_prev_sample;

wire tick_bit = tick_cnt[TICK_BITS-1];
wire tick     = tick_bit & ~tick_bit_prev; // one-cycle pulse, ~every 2^TICK_BITS cycles

initial begin
    tick_cnt        = 0;
    tick_bit_prev   = 1'b0;
    btn_prev_sample = 4'b0;
    btn_estable     = 4'b0;
end

always @(posedge clk) begin
    tick_cnt      <= tick_cnt + 1'b1;
    tick_bit_prev <= tick_bit;
    if (tick) begin
        if (btn_i == btn_prev_sample) btn_estable <= btn_i;
        btn_prev_sample <= btn_i;
    end
end

endmodule
