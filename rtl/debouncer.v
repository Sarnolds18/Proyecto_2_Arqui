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
// At 10 MHz (CLOCK_PERIOD = 100 ns), TICK_BITS=17 samples every ~13.1 ms,
// close to Proyecto 1's proven ~10 ms debounce window (on the FPGA at 25 MHz
// it was TICK_BITS=18, ~10.5 ms). Switch bounce settles well under that, so
// two agreeing samples ~13 ms apart is enough for stability.
//
// All state has an asynchronous reset to 0 (in an ASIC flip-flops power up
// undefined; there is no configuration step that clears them).

module debounce_bank #(
    parameter TICK_BITS = 17
) (
    input  wire       clk,
    input  wire       rst_ni,
    input  wire [3:0] btn_i,
    output reg  [3:0] btn_estable
);

reg [TICK_BITS-1:0] tick_cnt;
reg                 tick_bit_prev;
reg [3:0]           btn_prev_sample;

wire tick_bit = tick_cnt[TICK_BITS-1];
wire tick     = tick_bit & ~tick_bit_prev; // one-cycle pulse, ~every 2^TICK_BITS cycles

always @(posedge clk or negedge rst_ni) begin
    if (!rst_ni) begin
        tick_cnt        <= {TICK_BITS{1'b0}};
        tick_bit_prev   <= 1'b0;
        btn_prev_sample <= 4'b0;
        btn_estable     <= 4'b0;
    end else begin
        tick_cnt      <= tick_cnt + 1'b1;
        tick_bit_prev <= tick_bit;
        if (tick) begin
            if (btn_i == btn_prev_sample) btn_estable <= btn_i;
            btn_prev_sample <= btn_i;
        end
    end
end

endmodule
