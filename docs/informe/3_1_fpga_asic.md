# 3.1 Del RTL de FPGA al RTL de ASIC

## El top del macro: `asic_top`

`rtl/asic_top.v` instancia el SoC (`pochoco_soc u_pochoco`) y no contiene nada propio de
la Go Board. Sus puertos son terminales lógicos del macro, no pads de I/O:

| Puerto | Dir. | Función |
|---|---|---|
| `clk_i` | in | reloj (10 MHz en la corrida final, `CLOCK_PERIOD` = 100 ns) |
| `rst_ni` | in | reset asíncrono, activo bajo (no existía en el Proyecto 2) |
| `btn_i[3:0]` | in | botones |
| `led_o[3:0]` | out | LEDs |
| `seg1_o[6:0]`, `seg2_o[6:0]` | out | displays de 7 segmentos, `{G..A}`, **activo alto** |
| `spi_sclk_i`, `spi_mosi_i`, `spi_cs_ni`, `spi_miso_o` | in/out | esclavo SPI |

La estrategia de memoria (sección 3.2) se elige con un parámetro: ROM por defecto, o
flip-flops si se define `POCHOCO_MEM_FF`. `game_top.v` (el top de la FPGA) sigue en el
repositorio, pero esta rama ya no apunta a la Go Board: la versión para la placa es el
tag `p2-entrega`.

## Método

Para que cada construcción dependiente de la FPGA quedara respaldada por un mensaje del
flujo, se corrió LibreLane **antes de arreglar nada** y se guardaron las corridas en
`flow/asic_top/runs/`:

| Corrida | RTL | Qué mostró |
|---|---|---|
| `00_rtl_p2_sin_cambios` | RTL del P2 + `asic_top` | El flujo se detiene en la etapa 3 (`Checker.LintErrors`) por `SB_RAM40_4K`; tapa todo lo demás |
| `01_regfile_ff` | `00` + register file de flip-flops | Lint y síntesis pasan: aparecen los mensajes de los puntos 2–5 |
| `02_reset_externo` | `01` + reset externo y sin `initial` | Confirma que los mensajes de los puntos 4 y 5 desaparecen |

## Construcciones encontradas

| # | Construcción | Archivo | Mensaje de LibreLane (log:línea, en `flow/asic_top/runs/`) | Reemplazo |
|---|---|---|---|---|
| 1 | Primitiva `SB_RAM40_4K` (BRAM de la iCE40) | `espino_register_file.v` | `00_rtl_p2_sin_cambios/01-verilator-lint/verilator-lint.log:1` y `:13`: `%Error-MODMISSING ... 'SB_RAM40_4K'` | 15 × 32 flip-flops con lectura sincrónica y reset a 0 |
| 2 | `initial $readmemh` | `pochoco_ram.v` | `01_regfile_ff/06-yosys-synthesis/yosys-synthesis.log:1093` (`meminit`) y `:4102–4106` (`DFFLEGALIZE`); **sin warning** | Programa dentro del circuito: ROM generada por el assembler o valores de reset (3.2) |
| 3 | Inferencia de BRAM de 512 palabras | `pochoco_ram.v` | `01_regfile_ff/.../yosys-synthesis.log:1401–1406` (`MEMORY_MAP`: 512 × 32 FF) y `:4558` (2,31 mm²) | Memoria dimensionada al uso real (99 instrucciones, 0 datos) |
| 4 | Reset de encendido por valor inicial (`reg [12:0] por_cnt = 13'b0`) | `pochoco_soc.v` | `01_regfile_ff/01-verilator-lint/verilator-lint.log:7` (`PROCASSINIT`) y `:1` (`rst_ni` sin usar); `.../yosys-synthesis.log:304–305` (`PROC_INIT`) | Puerto `rst_ni` + sincronizador de 2 FF |
| 5 | `initial` y registros sin reset | `debouncer.v` | `01_regfile_ff/.../yosys-synthesis.log:299–303` (`PROC_INIT`); **sin warning** | Reset asíncrono a 0 |
| 6 | Reloj de 25 MHz supuesto | `debouncer.v`, `game.s` | Sin mensaje | `TICK_BITS` 18 → 17; constantes de `game.s` para 10 MHz |
| 7 | Inversión `~seg` (displays activo bajo de la placa) | `pochoco_soc.v` | Sin mensaje | Salidas activo alto; la inversión pasa a `game_top` |
| 8 | Botones asíncronos sin sincronizador | `debouncer.v` | Sin mensaje | 2 FF de sincronización por botón |

El extracto de cada mensaje está en `docs/evidencia.md`.

## Lo que mostró LibreLane

**Error explícito (1).** Solo `SB_RAM40_4K` detuvo el flujo. Es un bloque físico de la
iCE40 instanciado a mano en el register file (dos copias, para tener dos puertos de
lectura). La biblioteca `gf180mcu_fd_sc_mcu7t5v0` solo tiene celdas estándar y el
proyecto no usa macros SRAM, así que Verilator no encuentra el módulo. Se reescribió
`espino_register_file` con flip-flops, sin cambiar el nombre del módulo, los puertos ni
la instancia `u_rf`. Se mantuvo la **lectura sincrónica** de la BRAM, porque el core
depende de esa latencia de un ciclo (FSM `ops_valid_q` de `espino_id_stage.v`), y se
agregó **reset a 0** para reproducir el `INIT_0 = 0` de la BRAM. Costo: 544 flip-flops.
En la corrida final, el register file es el 45 % del área lógica (82.990 µm²,
`docs/img/bloques.csv`).

**Valores iniciales descartados en silencio (2, 4, 5).** El hallazgo central de esta
sección es que `$readmemh`, los bloques `initial` y el valor inicial de `por_cnt`
**no producen ningún error**. Yosys los convierte en atributos `init` (`PROC_INIT`,
`meminit`), y luego `DFFLEGALIZE` mapea esos flip-flops a celdas `dffq_1`, que no tienen
valor inicial (`yosys-synthesis.log:4106`: 16.488 FF). El valor desaparece del netlist
sin aviso. El único indicio fue el warning `PROCASSINIT` de Verilator sobre `por_cnt`.
En la FPGA esos valores existen porque el bitstream inicializa cada FF y cada BRAM al
configurarse. En silicio los FF arrancan en un valor indeterminado, lo que implica:

- **(2)** El programa no estaría en la memoria: el SoC ejecutaría basura.
- **(4)** `por_cnt` podría arrancar con el bit 12 en 1, y el SoC nunca pasaría por
  reset. En simulación del netlist queda en X y el reset no se suelta nunca.
- **(5)** El debouncer podría reportar botones falsos durante los primeros muestreos.

Reemplazos:

- El programa pasa a ser parte del circuito (3.2).
- `asic_top` tiene un puerto `rst_ni` que entra a un **sincronizador de 2 flip-flops**
  en `pochoco_soc`: aserción asíncrona (no necesita reloj) y liberación sincrónica (todos
  los FF salen de reset en el mismo flanco, sin violaciones de recovery/removal).
- `por_cnt` se eliminó: sus 4.096 ciclos de espera eran para que las BRAM de la iCE40 se
  estabilizaran.
- `debounce_bank` tiene reset asíncrono.

En `02_reset_externo` ya no aparecen ni `PROCASSINIT` ni las reglas `PROC_INIT`. Además,
en la simulación post-síntesis (3.7) todos los FF arrancan en X y el juego funciona: eso
muestra que el SoC ya no depende de valores iniciales.

**Área desbordada (3).** Sin BRAM, `MEMORY_MAP` convierte la RAM de 512 × 32 en 16.384
flip-flops con sus multiplexores. El diseño llega a 67.817 celdas y 2,31 mm² de área de
celdas, el 47,8 % secuencial (`yosys-synthesis.log:4558–4559`). No es un error, pero casi
toda esa área es memoria que el juego no usa. Con la memoria dimensionada al uso real
(99 instrucciones y 0 datos, `scripts/contar_palabras.py`), la corrida final tiene
196.097 µm² de celdas, unas 12 veces menos.

## Problemas que no generaron ningún mensaje

El flujo no tiene cómo detectarlos, porque son correctos para la síntesis y el STA. Son
supuestos sobre el entorno de la Go Board:

- **(6) Reloj.** Un contador de 18 bits o la constante 75.000.000 son igual de válidos
  para Yosys. Pero el ASIC corre a 10 MHz, no a los 25 MHz del oscilador de la placa, así
  que todo lo que mide tiempo contando ciclos queda 2,5 veces más lento: los 3 s de
  espera pasarían a 7,5 s, cada décima mostrada valdría 0,25 s y el debouncer muestrearía
  cada 26 ms. Se cambió `TICK_BITS` a 17 (2^17 / 10 MHz ≈ 13,1 ms) y se recalcularon
  las constantes de `game.s` (3.4).
- **(7) Polaridad de los displays.** El activo bajo es una propiedad de los displays de
  la Go Board, no del SoC. Un macro no sabe qué se le va a conectar, así que dejar la
  inversión adentro fijaría en silicio una convención de la placa. `asic_top` entrega los
  segmentos activo alto, y la inversión quedó solo en `game_top`.
- **(8) Botones asíncronos.** Un botón cambia en cualquier momento respecto del reloj.
  En el P2, los botones entraban directo a los flip-flops de muestreo. Si uno cambia
  dentro de la ventana de setup/hold, ese FF puede quedar metaestable. El STA no puede
  verificarlo, porque la entrada no tiene relación temporal con `clk_i`. En la FPGA nunca
  falló, pero en el ASIC nada lo garantiza. Se agregaron 2 FF en cadena por botón
  (8 FF en total), igual a lo que ya tenía el esclavo SPI. La latencia extra
  (2 ciclos) queda absorbida por el período de muestreo del debouncer.

## Verificación de los cambios

- `sim/tb_register_file.v`: reset, x0, lectura sincrónica, read-before-write y 2.000
  accesos aleatorios contra un modelo de referencia.
- `sim/tb_game_smoke.v`: con el register file nuevo da la misma salida y los mismos
  tiempos que con el modelo `SB_RAM40_4K`. Con el reset externo, los eventos se adelantan
  exactamente 4.090 ciclos (el reset de 4.096 ciclos pasa a ~6).
- `sim/tb_pochoco_periph.v` pasa.
- Lint de Verilator en la corrida final (`CP100_U40_final/01-verilator-lint/verilator-lint.log`):
  0 errores y 14 warnings, todos de señales o parámetros sin usar (`UNUSEDSIGNAL`,
  `UNUSEDPARAM`). Por ejemplo: bits altos de direcciones que la memoria no decodifica,
  `shamt` y los parámetros de shift de la ALU (los shifts están deshabilitados desde el
  P2) o `illegal_insn`. Ninguno es una construcción dependiente de la FPGA.
