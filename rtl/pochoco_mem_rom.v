// Course: Arquitectura de Computadores (2026)
// Proyecto 3 - Pochoco SoC de RTL a GDSII
//
// pochoco_mem_rom: estrategia de memoria 1 (seccion 3.2). Reemplaza a la RAM
// unificada del Proyecto 2 (BRAM del iCE40 cargada con $readmemh) por:
//
// - Puerto A (instrucciones): game_rom, ROM combinacional que genera
//   sw/assembler.py --rom desde game.s. La salida se registra (lectura
//   sincronica), igual que la BRAM: el core espera la instruccion un ciclo
//   despues de pedirla.
// - Puerto B (datos): RAM de flip-flops de DataWords palabras, con byte
//   enables y lectura sincronica como la RAM original. El juego usa 0
//   palabras de datos (scripts/contar_palabras.py); DataWords deja espacio
//   para guardar ra y algunos registros si un programa futuro llama
//   subrutinas anidadas. Los bits de direccion sobre la RAM se ignoran
//   (la RAM se repite en todo el espacio de datos, como la RAM original).
//   Sin reset: como una RAM, su contenido inicial es indefinido.
//
// Arquitectura Harvard: el puerto de datos no lee la ROM, asi que un
// programa no puede leer su propio codigo con lw (game.s no lo hace).

module pochoco_mem_rom #(
  parameter DataWords = 8
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
  output reg  [31:0] b_rdata_o
);

  // Instrucciones: direccion de palabra de 8 bits (256 palabras de ROM).
  wire [31:0] rom_data;

  game_rom u_rom (
    .addr_i (a_addr_i[9:2]),
    .data_o (rom_data)
  );

  always @(posedge clk_i) begin
    if (a_req_i) a_rdata_o <= rom_data;
  end

  // Datos
  localparam AddrW = $clog2(DataWords);

  reg  [31:0]      data_mem [0:DataWords-1];
  wire [AddrW-1:0] b_word = b_addr_i[AddrW+1:2];

  always @(posedge clk_i) begin
    if (b_req_i && b_we_i) begin
      if (b_be_i[0]) data_mem[b_word][7:0]   <= b_wdata_i[7:0];
      if (b_be_i[1]) data_mem[b_word][15:8]  <= b_wdata_i[15:8];
      if (b_be_i[2]) data_mem[b_word][23:16] <= b_wdata_i[23:16];
      if (b_be_i[3]) data_mem[b_word][31:24] <= b_wdata_i[31:24];
    end
    b_rdata_o <= data_mem[b_word];
  end

endmodule
