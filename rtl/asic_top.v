// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
// Proyecto 3 - Pochoco SoC de RTL a GDSII
//
// asic_top: top-level del macro para LibreLane (GF180MCU). Sus puertos son
// terminales logicos del macro, no pads de I/O: reloj, reset, LEDs, botones,
// los dos displays de 7 segmentos (activo alto) y SPI. A diferencia de
// game_top no hay pines ni polaridades propias de la Go Board.
//
// Estado actual: instancia pochoco_soc tal como se entrego en el Proyecto 2
// (tag p2-entrega), para que la primera corrida de LibreLane muestre las
// construcciones dependientes de la FPGA (ver docs/evidencia.md). Por eso
// rst_ni todavia no llega al SoC (este usa su POR interno) y seg1_o/seg2_o
// salen invertidos por pochoco_soc.

module asic_top (
  input  wire       clk_i,
  input  wire       rst_ni,

  output wire [3:0] led_o,
  input  wire [3:0] btn_i,

  output wire [6:0] seg1_o,  // {G,F,E,D,C,B,A}
  output wire [6:0] seg2_o,  // {G,F,E,D,C,B,A}

  input  wire       spi_sclk_i,
  input  wire       spi_mosi_i,
  input  wire       spi_cs_ni,
  output wire       spi_miso_o
);

  pochoco_soc #(
    .NumWords (512),
    .MemFile  ("../sw/game.hex")
  ) u_pochoco (
    .i_Clk        (clk_i),

    .o_LED        (led_o),
    .i_Switch     (btn_i),

    .o_Segment1_A (seg1_o[0]), .o_Segment1_B (seg1_o[1]),
    .o_Segment1_C (seg1_o[2]), .o_Segment1_D (seg1_o[3]),
    .o_Segment1_E (seg1_o[4]), .o_Segment1_F (seg1_o[5]),
    .o_Segment1_G (seg1_o[6]),
    .o_Segment2_A (seg2_o[0]), .o_Segment2_B (seg2_o[1]),
    .o_Segment2_C (seg2_o[2]), .o_Segment2_D (seg2_o[3]),
    .o_Segment2_E (seg2_o[4]), .o_Segment2_F (seg2_o[5]),
    .o_Segment2_G (seg2_o[6]),

    .i_SPI_SCLK   (spi_sclk_i),
    .i_SPI_MOSI   (spi_mosi_i),
    .i_SPI_CS_n   (spi_cs_ni),
    .o_SPI_MISO   (spi_miso_o)
  );

endmodule
