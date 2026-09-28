// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
// Proyecto 2 - Juego de reflejos
//
// Debounce for the 4 buttons/switches. Uses one shared slow "tick" instead
// of a per-button counter+comparator (like proyecto1/src/debouncer.v):
// the SoC leaves very little LUT headroom on the iCE40 HX1K, so 4
// independent debouncers don't fit. A free-running TICK_BITS-wide
// counter's own MSB toggling serves directly as the sample enable (no
// comparator needed), and the 4 buttons are accepted together with one
// 4-bit equality check between two consecutive samples.
//
// At 25 MHz, TICK_BITS=18 samples every ~10.5 ms, matching Proyecto 1's
// proven ~10 ms debounce window. Switch bounce settles well under that, so
// two agreeing samples 10 ms apart is enough for stability.

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
