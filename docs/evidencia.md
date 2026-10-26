# Evidencia FPGA → ASIC (sección 3.1)

Construcciones del RTL del Proyecto 2 (tag `p2-entrega`) que dependen de la FPGA, el
mensaje de LibreLane que las evidenció y cómo se reemplazaron. Cada log citado debe
existir en el repo (corrida guardada en `runs/`).

| # | Construcción | Archivo | Mensaje de LibreLane (log:línea) | Reemplazo |
|---|---|---|---|---|
| 1 | Primitiva `SB_RAM40_4K` (iCE40) | `rtl/espino_core/espino_register_file.v` | pendiente | pendiente |
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

pendiente

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
