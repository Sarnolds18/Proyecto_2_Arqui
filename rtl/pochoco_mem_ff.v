// Course: Arquitectura de Computadores (2026)
// Proyecto 3 - Pochoco SoC de RTL a GDSII
//
// pochoco_mem_ff: estrategia de memoria 2 (seccion 3.2). Memoria unificada
// de instrucciones y datos hecha de flip-flops, como la RAM del Proyecto 2
// pero dimensionada a lo que usa el juego: NumWords = 99 palabras de
// programa + 8 de datos (las mismas que la estrategia 1, para comparar con
// la misma capacidad).
//
// En vez de $readmemh, el programa se carga en el reset: cada palabra i
// toma el valor de game_rom en la direccion constante i. Como la direccion
// es constante, la sintesis reduce cada instancia de game_rom a constantes
// y cada flip-flop queda con reset a 0 o set a 1 segun su bit del programa;
// no queda ninguna ROM en el circuito. (Yosys avisa "Async reset value ...
// is not constant" una vez por palabra al procesar los always antes de
// aplanar; despues de aplanar el valor si es constante.)
//
// Los dos puertos leen de forma sincronica, igual que la RAM original. Una
// direccion fuera de la memoria lee 0 (no-op para el core) e ignora
// escrituras. Las direcciones de datos y de instrucciones son las mismas,
// como en la RAM unificada: los datos van despues del codigo.

module pochoco_mem_ff #(
  parameter NumWords = 107
) (
  input  wire        clk_i,
  input  wire        rst_ni,

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

  // Direccion de palabra de 8 bits, igual que game_rom. El indice de mem
  // usa solo IdxBits; los bits altos ya quedan cubiertos por word < Words.
  localparam [7:0] Words   = NumWords;
  localparam       IdxBits = $clog2(NumWords);

  wire [7:0] a_word = a_addr_i[9:2];
  wire [7:0] b_word = b_addr_i[9:2];

  reg  [31:0] mem      [0:NumWords-1];
  wire [31:0] init_word [0:NumWords-1];

  genvar i;
  generate
    for (i = 0; i < NumWords; i = i + 1) begin : g_word
      localparam [7:0] Addr = i;

      game_rom u_init (
        .addr_i (Addr),
        .data_o (init_word[i])
      );

      always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
          mem[i] <= init_word[i];
        end else if (b_req_i && b_we_i && b_word == Addr) begin
          if (b_be_i[0]) mem[i][7:0]   <= b_wdata_i[7:0];
          if (b_be_i[1]) mem[i][15:8]  <= b_wdata_i[15:8];
          if (b_be_i[2]) mem[i][23:16] <= b_wdata_i[23:16];
          if (b_be_i[3]) mem[i][31:24] <= b_wdata_i[31:24];
        end
      end
    end
  endgenerate

  always @(posedge clk_i) begin
    if (a_req_i) a_rdata_o <= (a_word < Words) ? mem[a_word[IdxBits-1:0]] : 32'h0;
  end

  always @(posedge clk_i) begin
    b_rdata_o <= (b_word < Words) ? mem[b_word[IdxBits-1:0]] : 32'h0;
  end

endmodule
