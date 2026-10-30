# Evidencia FPGA → ASIC (sección 3.1)

Construcciones del RTL del Proyecto 2 (tag `p2-entrega`) que dependen de la FPGA, el
mensaje de LibreLane que las evidenció y cómo se reemplazaron. Cada log citado debe
existir en el repo (corrida guardada en `flow/asic_top/runs/`).

## Corridas

| Corrida | RTL | Resultado |
|---|---|---|
| `00_rtl_p2_sin_cambios` | Tag `p2-entrega` + `rtl/asic_top.v` | Se detiene en la etapa 3 de 80 (`Checker.LintErrors`): 2 errores de lint (`flow.log:7`, `error.log:1`) |

| # | Construcción | Archivo | Mensaje de LibreLane (log:línea) | Reemplazo |
|---|---|---|---|---|
| 1 | Primitiva `SB_RAM40_4K` (iCE40) | `rtl/espino_core/espino_register_file.v` | `flow/asic_top/runs/00_rtl_p2_sin_cambios/01-verilator-lint/verilator-lint.log:1` y `:13` (`%Error-MODMISSING`) | Banco de 15×32 flip-flops con lectura sincrónica y reset a 0 |
| 2 | `initial $readmemh` | `rtl/pochoco_ram.v` | pendiente | pendiente |
| 3 | Inferencia de BRAM (512 palabras) | `rtl/pochoco_ram.v` | pendiente | pendiente |
| 4 | Reset de encendido por valor inicial (`reg [12:0] por_cnt = 13'b0`) | `rtl/pochoco_soc.v` | pendiente | pendiente |
| 5 | Bloque `initial` y registros sin reset | `rtl/debouncer.v` | pendiente | pendiente |
| 6 | Supuesto de reloj de 25 MHz (`TICK_BITS`, constantes de `game.s`) | `rtl/debouncer.v`, `sw/game.s` | pendiente | pendiente |
| 7 | Inversión `~seg` para displays activo-bajo de la Go Board | `rtl/pochoco_soc.v` | pendiente | pendiente |

## Detalle por construcción

Para cada fila: extracto del mensaje, explicación de por qué es un problema en ASIC y
descripción del cambio. Si una construcción no produjo ningún mensaje del flujo, se
explica por qué igual era un problema.

### 1. `SB_RAM40_4K`

Corrida `00_rtl_p2_sin_cambios`, `01-verilator-lint/verilator-lint.log`:

```
1:  %Error-MODMISSING: .../rtl/espino_core/espino_register_file.v:22:3: Cannot find file containing module: 'SB_RAM40_4K'
13: %Error-MODMISSING: .../rtl/espino_core/espino_register_file.v:33:3: Cannot find file containing module: 'SB_RAM40_4K'
16: %Error: Exiting due to 2 error(s)
```

`SB_RAM40_4K` es un bloque de RAM físico de la iCE40, instanciado directamente en el
banco de registros (dos copias para tener dos puertos de lectura). En el ASIC no existe:
la biblioteca `gf180mcu_fd_sc_mcu7t5v0` solo tiene celdas estándar y el proyecto no usa
macros SRAM. Verilator no encuentra el módulo y LibreLane detiene el flujo en
`Checker.LintErrors` antes de llegar a síntesis, por lo que esta corrida no alcanza a
mostrar las demás construcciones de la tabla.

Reemplazo: `espino_register_file` reescrito con flip-flops (mismo nombre de módulo y
puertos, instancia `u_rf` sin cambios):

- x1..x15 como 15 registros de 32 bits; x0 no se almacena y se lee como 0.
- **Lectura sincrónica**: `rdata_a_o`/`rdata_b_o` son registros, igual que la salida
  de `SB_RAM40_4K`. El core depende de esa latencia de un ciclo (FSM `ops_valid_q` en
  `espino_id_stage.v`), así que no se cambió a lectura combinacional.
- **Reset a 0** con `rst_ni`, para reproducir el `INIT_0 = 0` de las BRAM: en la FPGA
  los registros arrancaban en 0 y en ASIC los flip-flops arrancan indeterminados.
- Costo: 15×32 + 2×32 = 544 flip-flops (antes, 0 FF y 4 BRAM).

Verificación: `sim/tb_register_file.v` (reset, x0, lectura sincrónica,
read-before-write y 2000 accesos aleatorios contra un modelo de referencia) pasa, y
`sim/tb_game_smoke.v` da exactamente la misma salida y los mismos tiempos que con el
modelo `SB_RAM40_4K` de `cells_sim.v`.

### 2. `initial $readmemh`

pendiente

### 3. Inferencia de BRAM

pendiente

### 4. Reset de encendido por valor inicial

pendiente

### 5. `initial` en `debounce_bank`

pendiente

### 6. Supuesto de reloj de 25 MHz

pendiente

### 7. Inversión de los 7 segmentos

pendiente
