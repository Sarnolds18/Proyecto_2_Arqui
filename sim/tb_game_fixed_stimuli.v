// Course: Arquitectura de Computadores (2026)
// Proyecto 3 - Pochoco SoC de RTL a GDSII
//
// tb_game_fixed_stimuli: testbench de la seccion 3.7. Simula asic_top con el
// juego y aprieta los botones en ciclos fijos (no reacciona a los LEDs como
// tb_game_smoke), para que la simulacion RTL y la del netlist post-sintesis
// reciban exactamente los mismos estimulos. Se corre con
// sim/run_fixed_stimuli.sh, que compila este mismo archivo contra el RTL o
// contra el netlist.
//
// Programa: sim/build/game_sim.s, generado por scripts/game_sim.py desde
// sw/game.s con los tiempos / 100 (3 s = 300.000 ciclos, 2 s = 200.000,
// 1 decima = 10.000). El hardware no cambia: el debounce sigue con
// TICK_BITS = 17 (muestrea cada 131.072 ciclos, un cambio se acepta tras 2
// muestras iguales), por eso cada pulsacion se mantiene PRESS_HOLD ciclos.
//
// Escenario (los ciclos salen de una corrida RTL: el juego es determinista
// desde el reset porque el PRNG se siembra con el contador de ciclos):
//   1. Ronda 1: se aprieta un boton que no es el objetivo -> el display
//      muestra "EE" y la ronda se reinicia (los 4 LEDs vuelven a 1111).
//   2. Ronda 1 de nuevo: se aprieta el boton correcto -> el display muestra
//      el tiempo en decimas.
//
// Salida: una linea por cada cambio de los puertos de salida (LEDs y
// displays) con el ciclo en que ocurrio, mas un resumen por ronda. Como solo
// mira puertos de asic_top, la misma salida sirve para el RTL y el netlist:
// run_fixed_stimuli.sh compara los dos logs linea por linea.

`timescale 1ns/1ps

module tb_game_fixed_stimuli;

  localparam PRESS_HOLD = 300_000;  // > 2 * 2^17 ciclos de debounce + 2 del sincronizador
  localparam END_CYCLE  = 1_600_000;

  // Estimulos: ciclo en que se aprieta y boton (one-hot). El boton se suelta
  // PRESS_HOLD ciclos despues.
  localparam [31:0] PRESS1_CYCLE = 350_000;   // ronda 1, objetivo 0010: boton incorrecto
  localparam [3:0]  PRESS1_BTN   = 4'b0001;
  localparam [31:0] PRESS2_CYCLE = 1_000_000; // ronda 1 reiniciada, objetivo 0010: boton correcto
  localparam [3:0]  PRESS2_BTN   = 4'b0010;

  reg clk = 1'b0;
  always #50 clk = ~clk;  // 100 ns = CLOCK_PERIOD de la corrida final

  reg        rst_n = 1'b0;
  reg  [3:0] btn   = 4'b0000;
  wire [3:0] led;
  wire [6:0] seg1, seg2;
  wire       miso;

  asic_top dut (
    .clk_i      (clk),
    .rst_ni     (rst_n),
    .led_o      (led),
    .btn_i      (btn),
    .seg1_o     (seg1),
    .seg2_o     (seg2),
    .spi_sclk_i (1'b0),
    .spi_mosi_i (1'b0),
    .spi_cs_ni  (1'b1),
    .spi_miso_o (miso)
  );

  // Ciclo actual: 0 en el primer flanco despues de soltar el reset.
  integer cycle = -10;
  always @(posedge clk) cycle <= cycle + 1;

  // Estimulos: los cambios se aplican en el flanco de bajada, lejos del
  // flanco de subida en que los muestrea el diseno.
  initial begin
    repeat (10) @(negedge clk);
    rst_n = 1'b1;
  end

  always @(negedge clk) begin
    if (cycle == PRESS1_CYCLE) btn = PRESS1_BTN;
    if (cycle == PRESS2_CYCLE) btn = PRESS2_BTN;
    if (cycle == PRESS1_CYCLE + PRESS_HOLD ||
        cycle == PRESS2_CYCLE + PRESS_HOLD) btn = 4'b0000;
    if (cycle == END_CYCLE) begin
      report_and_finish;
    end
  end

  // Inverso de hex2seg (pochoco_periph.v), para leer el display.
  function [7:0] seg2char;
    input [6:0] s;
    begin
      case (s)
        7'b0111111: seg2char = "0";  7'b0000110: seg2char = "1";
        7'b1011011: seg2char = "2";  7'b1001111: seg2char = "3";
        7'b1100110: seg2char = "4";  7'b1101101: seg2char = "5";
        7'b1111101: seg2char = "6";  7'b0000111: seg2char = "7";
        7'b1111111: seg2char = "8";  7'b1101111: seg2char = "9";
        7'b1110111: seg2char = "A";  7'b1111100: seg2char = "b";
        7'b0111001: seg2char = "C";  7'b1011110: seg2char = "d";
        7'b1111001: seg2char = "E";  7'b1110001: seg2char = "F";
        default:    seg2char = "?";
      endcase
    end
  endfunction

  function is_digit;
    input [7:0] c;
    is_digit = (c >= "0" && c <= "9");
  endfunction

  // Registro de eventos y chequeos, todo desde los puertos de asic_top.
  reg  [17:0] outs_q;
  wire [17:0] outs = {led, seg1, seg2};
  reg  [7:0]  c1, c2;

  integer errors        = 0;
  integer target_cycle  = -1;    // ciclo en que se encendio el LED objetivo
  reg [3:0] target_led  = 4'b0;
  integer wrong_seen    = 0;     // "EE" en el display
  integer restart_seen  = 0;     // 1111 de nuevo despues de "EE"
  integer correct_count = 0;

  always @(posedge clk) begin
    if (rst_n && cycle >= 0) begin
      outs_q <= outs;
      if (outs !== outs_q) begin
        c1 = seg2char(seg1);
        c2 = seg2char(seg2);
        $display("ciclo %8d  led=%b  display=%s%s", cycle, led, c1, c2);

        if (led == 4'b0001 || led == 4'b0010 || led == 4'b0100 || led == 4'b1000) begin
          if (led !== outs_q[17:14]) begin
            target_cycle = cycle;
            target_led   = led;
          end
        end

        if (c1 == "E" && c2 == "E" && seg1 !== outs_q[13:7]) begin
          wrong_seen = wrong_seen + 1;
          $display("  -> boton incorrecto: display EE (objetivo era %b)", target_led);
        end

        if (led == 4'b1111 && outs_q[17:14] !== 4'b1111 && wrong_seen > restart_seen) begin
          restart_seen = restart_seen + 1;
          $display("  -> ronda reiniciada: LEDs = 1111 de nuevo");
        end

        // En una ronda correcta el resultado aparece con el LED objetivo
        // todavia encendido (con boton incorrecto los LEDs se apagan antes).
        if (is_digit(c1) && is_digit(c2) && {seg1, seg2} !== outs_q[13:0]
            && target_cycle >= 0 && led === target_led) begin
          correct_count = correct_count + 1;
          $display("  -> ronda correcta %0d: objetivo %b encendido en el ciclo %0d, resultado en el ciclo %0d (%0d ciclos), display = %s%s decimas",
                   correct_count, target_led, target_cycle, cycle, cycle - target_cycle, c1, c2);
          target_cycle = -1;
        end
      end
    end else begin
      outs_q <= outs;
    end
  end

`ifndef GATE_LEVEL
  // Solo RTL (en el netlist no quedan estas senales): confirmacion dinamica
  // del conteo de palabras de scripts/contar_palabras.py.
  integer max_pc       = 0;
  integer ram_accesses = 0;
  always @(posedge clk) begin
    if (dut.u_pochoco.instr_req && dut.u_pochoco.instr_addr > max_pc)
      max_pc = dut.u_pochoco.instr_addr;
    if (dut.u_pochoco.ram_b_req)
      ram_accesses = ram_accesses + 1;
  end
`endif

  task report_and_finish;
    begin
      $display("---");
`ifndef GATE_LEVEL
      // La ultima palabra pedida puede ser una mas que el programa: el fetch
      // pide PC+4 antes de que el salto final redirija (lee 0 = no-op).
      $display("RTL: direccion de instruccion mas alta pedida = 0x%0h (palabra %0d), accesos de datos a RAM = %0d",
               max_pc, max_pc / 4, ram_accesses);
`endif
      if (wrong_seen < 1)    begin $display("FAIL: no aparecio EE tras el boton incorrecto"); errors = errors + 1; end
      if (restart_seen < 1)  begin $display("FAIL: la ronda no se reinicio tras el boton incorrecto"); errors = errors + 1; end
      if (correct_count < 1) begin $display("FAIL: ninguna ronda correcta medida"); errors = errors + 1; end
      if (errors == 0) $display("PASS: boton incorrecto reinicia la ronda y la ronda correcta se mide");
      $finish;
    end
  endtask

endmodule
