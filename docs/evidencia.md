# Evidencia FPGA → ASIC (sección 3.1)

Construcciones del RTL del Proyecto 2 (tag `p2-entrega`) que dependen de la FPGA, el
mensaje de LibreLane que las evidenció y cómo se reemplazaron. Cada log citado debe
existir en el repo (corrida guardada en `flow/asic_top/runs/`).

## Corridas

| Corrida | RTL | Resultado |
|---|---|---|
| `00_rtl_p2_sin_cambios` | Tag `p2-entrega` + `rtl/asic_top.v` | Se detiene en la etapa 3 de 80 (`Checker.LintErrors`): 2 errores de lint (`flow.log:7`, `error.log:1`) |
| `01_regfile_ff` | `00` + register file de flip-flops (#1 resuelto) | Corrida con `--to OpenROAD.STAPrePNR` (etapas 1–12): lint y síntesis pasan sin errores. Ningún mensaje de error por #2–#5: Yosys los acepta y descarta los valores iniciales en silencio (ver detalle) |

| # | Construcción | Archivo | Mensaje de LibreLane (log:línea) | Reemplazo |
|---|---|---|---|---|
| 1 | Primitiva `SB_RAM40_4K` (iCE40) | `rtl/espino_core/espino_register_file.v` | `flow/asic_top/runs/00_rtl_p2_sin_cambios/01-verilator-lint/verilator-lint.log:1` y `:13` (`%Error-MODMISSING`) | Banco de 15×32 flip-flops con lectura sincrónica y reset a 0 |
| 2 | `initial $readmemh` | `rtl/pochoco_ram.v` | `flow/asic_top/runs/01_regfile_ff/06-yosys-synthesis/yosys-synthesis.log:1093` (`meminit`) y `:4102`–`4106` (`DFFLEGALIZE`); sin warning | pendiente (3.2) |
| 3 | Inferencia de BRAM (512 palabras) | `rtl/pochoco_ram.v` | `flow/asic_top/runs/01_regfile_ff/06-yosys-synthesis/yosys-synthesis.log:1401`–`1406` (`MEMORY_MAP`) y `:4532`, `:4558` (estadísticas) | pendiente (3.2) |
| 4 | Reset de encendido por valor inicial (`reg [12:0] por_cnt = 13'b0`) | `rtl/pochoco_soc.v` | `flow/asic_top/runs/01_regfile_ff/01-verilator-lint/verilator-lint.log:7` (`%Warning-PROCASSINIT`), `flow/asic_top/runs/01_regfile_ff/06-yosys-synthesis/yosys-synthesis.log:304`–`305` (`PROC_INIT`) y `:4102`–`4106`; además `verilator-lint.log:1` (`rst_ni` sin usar) | pendiente (P3-04) |
| 5 | Bloque `initial` y registros sin reset | `rtl/debouncer.v` | `flow/asic_top/runs/01_regfile_ff/06-yosys-synthesis/yosys-synthesis.log:299`–`303` (`PROC_INIT`) y `:4102`–`4106`; sin warning | pendiente (P3-04) |
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

Corrida `01_regfile_ff`, `06-yosys-synthesis/yosys-synthesis.log`:

```
1093: Removed top 23 address bits (of 32) from memory init port asic_top.$flatten\u_pochoco.\u_ram.$meminit$\mem$.../rtl/pochoco_ram.v:36$123 (u_pochoco.u_ram.mem).
4102: 155.1. Executing DFFLEGALIZE pass (convert FFs to types supported by the target).
4103: Mapping DFF cells in module `\asic_top':
4104:   mapped 738 $_DFF_PN0_ cells to \gf180mcu_fd_sc_mcu7t5v0__dffrnq_1 cells.
4105:   mapped 3 $_DFF_PN1_ cells to \gf180mcu_fd_sc_mcu7t5v0__dffsnq_1 cells.
4106:   mapped 16488 $_DFF_P_ cells to \gf180mcu_fd_sc_mcu7t5v0__dffq_1 cells.
```

Yosys sí lee `game.hex` (resuelve la ruta relativa al archivo fuente) y lo guarda como
puerto de inicialización de la memoria (`meminit`, línea 1093). Pero al convertir la
memoria a flip-flops ese contenido solo puede quedar como valor inicial de cada FF, y
las celdas de GF180 no tienen valor inicial: `DFFLEGALIZE` mapea los 16.488 FF sin reset
a `dffq_1` (línea 4106) y el contenido del programa desaparece del netlist **sin ningún
warning ni error** (`warning.log` solo tiene los avisos de lint y de SDC). En la FPGA el
bitstream carga el contenido de la BRAM al configurarse; en el silicio no hay ningún
mecanismo que lo haga, así que el SoC arrancaría ejecutando memoria indeterminada.

Reemplazo: pendiente (sección 3.2, las dos estrategias de memoria).

### 3. Inferencia de BRAM

Corrida `01_regfile_ff`, `06-yosys-synthesis/yosys-synthesis.log`:

```
1401: Mapping memory \u_pochoco.u_ram.mem in module \asic_top:
1402:   created 512 $dff cells and 0 static cells of width 32.
1405:   read interface: 2 $dff and 1022 $mux cells.
1406:   write interface: 2048 write mux blocks.
4532:     16488 1.05E+06   gf180mcu_fd_sc_mcu7t5v0__dffq_1
4558:    Chip area for module '\asic_top': 2312311.724800
4559:      of which used for sequential elements: 1104958.310400 (47.79%)
```

En la iCE40 la RAM de 512×32 se infería como bloques BRAM (0 LUT/FF). Sin macros SRAM
no hay donde inferirla: `MEMORY_MAP` la convierte en 512×32 = 16.384 flip-flops más
sus multiplexores de lectura y escritura. El diseño completo queda en 67.817 celdas y
2,31 mm² de área de celdas, casi la mitad en elementos secuenciales. No es un error del
flujo, pero el área se dispara y casi toda es memoria que el juego no usa: el
programa ocupa 99 palabras de instrucción y 0 de datos.

Reemplazo: pendiente (sección 3.2, memoria dimensionada al uso real).

### 4. Reset de encendido por valor inicial

Corrida `01_regfile_ff`:

```
01-verilator-lint/verilator-lint.log:
1: %Warning-UNUSEDSIGNAL: rtl/asic_top.v:22:21: Signal is not used: 'rst_ni'
7: %Warning-PROCASSINIT: rtl/pochoco_soc.v:38:25: Procedural assignment to declaration with initial value: 'por_cnt'

06-yosys-synthesis/yosys-synthesis.log:
304: Found init rule in `$paramod$...\pochoco_soc.$proc$rtl/pochoco_soc.v:38$20'.
305:   Set init value: \por_cnt = 13'0000000000000
```

Verilator avisa que `por_cnt` tiene valor inicial en la declaración y además se asigna
en un `always`. Yosys lo convierte en un atributo `init` (línea 305), que se pierde en
`DFFLEGALIZE` (líneas 4102–4106) igual que en el punto 2. En la FPGA todos los FF valen
0 después de configurar, así que `por_cnt` contaba de 0 a 4096 y soltaba el reset. En
el ASIC arranca en un valor indeterminado: si `por_cnt[12]` arranca en 1 el SoC nunca
pasa por reset, y en simulación queda en X y el reset no se suelta nunca. El warning
de la línea 1 muestra la otra cara del problema: `asic_top` tiene un puerto `rst_ni`
que todavía no llega a ningún lado.

Reemplazo: pendiente (P3-04).

### 5. `initial` en `debounce_bank`

Corrida `01_regfile_ff`, `06-yosys-synthesis/yosys-synthesis.log`:

```
299: Found init rule in `$paramod\debounce_bank\TICK_BITS=s32'00000000000000000000000000010010.$proc$rtl/debouncer.v:36$130'.
300:   Set init value: \btn_estable = 4'0000
301:   Set init value: \tick_cnt = 18'000000000000000000
302:   Set init value: \tick_bit_prev = 1'0
303:   Set init value: \btn_prev_sample = 4'0000
```

El bloque `initial` es la única inicialización de estos registros (no tienen reset).
Yosys lo acepta sin warning y los valores se pierden en `DFFLEGALIZE`. La consecuencia
es más leve que en el punto 4 (`tick_cnt` es de libre corrida y `btn_estable` se
corrige en el primer muestreo), pero hasta los primeros dos muestreos de `tick` el SoC puede
leer botones falsos, y en simulación del netlist los registros quedan en X.

Reemplazo: pendiente (P3-04).

### 6. Supuesto de reloj de 25 MHz

pendiente

### 7. Inversión de los 7 segmentos

pendiente
