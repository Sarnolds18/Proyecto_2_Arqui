// Proyecto 3 - Pochoco SoC de RTL a GDSII
//
// PROVISORIO. Reemplazo de rtl/pochoco_ram.v (mismo nombre de modulo y mismos
// puertos, asi pochoco_soc no cambia) que permite correr el flujo completo
// mientras se implementan las dos estrategias de memoria de la seccion 3.2.
// Solo lo usa flow/asic_top_rom_provisoria/; no es parte del diseno final.
//
// - Puerto A (instrucciones): game_rom (rtl/game_rom.v) con lectura
//   sincronica, igual que la BRAM original: el core espera el dato un ciclo
//   despues de pedirlo.
// - Puerto B (datos): sin RAM. Lee 0 e ignora escrituras; el juego no usa
//   palabras de datos (no hay pila ni lw/sw fuera de MMIO).

module pochoco_ram #(
  parameter NumWords = 2048,  // sin uso: el tamano lo fija game_rom
  parameter MemFile  = ""     // sin uso: el programa esta en game_rom
) (
  input  wire        clk_i,

  // Port A: instruction
  input  wire        a_req_i,
  input  wire [31:0] a_addr_i,
  output reg  [31:0] a_rdata_o,

  // Port B: data
  input  wire        b_req_i,
  input  wire        b_we_i,
  input  wire [3:0]  b_be_i,
  input  wire [31:0] b_addr_i,
  input  wire [31:0] b_wdata_i,
  output wire [31:0] b_rdata_o
);

  wire [31:0] rom_data;

  game_rom u_rom (
    .addr_i (a_addr_i[9:2]),
    .data_o (rom_data)
  );

  always @(posedge clk_i) begin
    if (a_req_i) a_rdata_o <= rom_data;
  end

  assign b_rdata_o = 32'b0;

endmodule
