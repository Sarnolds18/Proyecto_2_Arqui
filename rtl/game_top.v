// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
// Proyecto 2 - Juego de reflejos
//
// game_top: the FPGA top-level for the reflex game. It just wires the Go
// Board's physical pins (see goboard.pcf) straight into pochoco_soc, which
// boots sw/game.hex. All the game logic lives in sw/game.s; there is no
// extra glue logic here on purpose, since pochoco_soc + game.s already do
// everything the game needs (LEDs, buttons, 7-seg, cycle counter).

module game_top (
  input  wire       i_Clk,

  output wire [3:0] o_LED,
  input  wire [3:0] i_Switch,

  output wire       o_Segment1_A, o_Segment1_B, o_Segment1_C, o_Segment1_D,
  output wire       o_Segment1_E, o_Segment1_F, o_Segment1_G,
  output wire       o_Segment2_A, o_Segment2_B, o_Segment2_C, o_Segment2_D,
  output wire       o_Segment2_E, o_Segment2_F, o_Segment2_G,

  input  wire       i_SPI_SCLK,
  input  wire       i_SPI_MOSI,
  input  wire       i_SPI_CS_n,
  output wire       o_SPI_MISO
);

  pochoco_soc #(
    .NumWords (512),
    .MemFile  ("sw/game.hex")
  ) u_pochoco (
    .i_Clk        (i_Clk),

    .o_LED        (o_LED),
    .i_Switch     (i_Switch),

    .o_Segment1_A (o_Segment1_A), .o_Segment1_B (o_Segment1_B),
    .o_Segment1_C (o_Segment1_C), .o_Segment1_D (o_Segment1_D),
    .o_Segment1_E (o_Segment1_E), .o_Segment1_F (o_Segment1_F),
    .o_Segment1_G (o_Segment1_G),
    .o_Segment2_A (o_Segment2_A), .o_Segment2_B (o_Segment2_B),
    .o_Segment2_C (o_Segment2_C), .o_Segment2_D (o_Segment2_D),
    .o_Segment2_E (o_Segment2_E), .o_Segment2_F (o_Segment2_F),
    .o_Segment2_G (o_Segment2_G),

    .i_SPI_SCLK   (i_SPI_SCLK),
    .i_SPI_MOSI   (i_SPI_MOSI),
    .i_SPI_CS_n   (i_SPI_CS_n),
    .o_SPI_MISO   (o_SPI_MISO)
  );

endmodule
