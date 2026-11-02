# Timing (sección 3.4)

## Barrido de `CLOCK_PERIOD` con la configuración final (L4)

Configuración de la corrida final (`flow/asic_top/config.json`): RTL con L6, memoria
ROM, jerarquía conservada, sin celdas de retardo (`EXTRA_EXCLUDED_CELLS =
gf180mcu_fd_sc_mcu7t5v0__dly*`), DRC de KLayout y pines por función.
`FP_CORE_UTIL` = 40 %. Métricas en `results/timing.csv`, generado con:

```bash
scripts/run_sweep.sh -d flow/asic_top -s final -p "60 50 40" -u 40
scripts/run_sweep.sh -d flow/asic_top -s finalmargen -p "40 35" -u 40 -c "PL_RESIZER_SETUP_SLACK_MARGIN=14"
python3 scripts/extract_metrics.py -o results/timing.csv flow/asic_top/runs/CP100_U40_final \
  flow/asic_top/runs/CP60_U40_final flow/asic_top/runs/CP50_U40_final \
  flow/asic_top/runs/CP40_U40_final flow/asic_top/runs/CP40_U40_finalmargen \
  flow/asic_top/runs/CP35_U40_finalmargen
```

Típico = `nom_tt_025C_5v00`, más lento = `max_ss_125C_4v50` (WNS / TNS en ns). En las 6
corridas, Magic DRC = 0, KLayout DRC = 0, LVS limpio y antena = 0.

| Corrida | T (ns) | Variante | Setup típico | Setup lento | Hold típico | Hold lento | Área celdas (µm²) | Celdas | ¿Cierra? |
|---|---:|---|---|---|---|---|---:|---:|---|
| `CP100_U40_final` | 100 | por defecto (**corrida final**) | 73,95 / 0 | 51,40 / 0 | 0,390 / 0 | 0,970 / 0 | 196.097 | 9.651 | sí |
| `CP60_U40_final` | 60 | por defecto | 34,03 / 0 | 11,40 / 0 | 0,390 / 0 | 0,970 / 0 | 196.097 | 9.651 | sí |
| `CP50_U40_final` | 50 | por defecto | 24,03 / 0 | 1,40 / 0 | 0,390 / 0 | 0,970 / 0 | 196.097 | 9.651 | sí |
| `CP40_U40_final` | 40 | por defecto | 14,03 / 0 | **−8,60 / −1.928,45** | 0,390 / 0 | 0,970 / 0 | 196.097 | 9.651 | **no** |
| `CP40_U40_finalmargen` | 40 | `PL_RESIZER_SETUP_SLACK_MARGIN = 14` | 20,58 / 0 | 3,55 / 0 | 0,390 / 0 | 0,970 / 0 | 197.320 | 9.654 | sí |
| `CP35_U40_finalmargen` | 35 | `PL_RESIZER_SETUP_SLACK_MARGIN = 14` | 19,60 / 0 | 6,09 / 0 | 0,391 / 0 | 0,971 / 0 | 204.154 | 9.707 | sí |

**Menor período que cierra en todos los corners: 35 ns (28,6 MHz)**, con margen de
setup en el resizer; con la configuración por defecto, **50 ns (20 MHz)**. Un punto a
30 ns con margen se lanzó pero no terminó (falta de espacio en disco), así que el
mínimo podría ser algo menor que 35 ns. Con el peor hold (0,13-0,14 ns en
los corners `ff`) todas cierran.

**Re-optimización.** Con la configuración por defecto, de 100 a 40 ns el circuito es
**el mismo** (196.097 µm², 9.651 celdas): el resizer no ve violaciones
(`RSZ-0098 No setup violations found` en
`37-openroad-resizertimingpostcts/openroad-resizertimingpostcts.log` de `CP60`, `CP50`
y `CP40_U40_final`) porque su estimación de parásitos es optimista (ver abajo, mismo
efecto que en la configuración anterior). A 40 ns eso deja 498 endpoints violando en
`max_ss`. Con el margen de 14 ns el resizer sí trabaja, y cuanto más corto el período,
más cambia el circuito:

| | 40 ns con margen | 35 ns con margen |
|---|---:|---:|
| Endpoints reparados (`RSZ-0099`, línea 30) | 787 | 898 |
| Celdas agrandadas (`RSZ-0051`) | 175 (línea 924) | 693 (línea 264) |
| Buffers insertados (`RSZ-0040`) | 3 (línea 923) | 53 (línea 263) |
| Intercambio de pines (`RSZ-0043`) | 3 (línea 925) | 42 (línea 265) |
| Área de celdas vs. corrida final | +0,6 % | +4,1 % |
| Retardo de datos de la ruta crítica (`max_ss`) | 35,28 ns | 27,91 ns |

### Ruta crítica de la corrida final

`CP100_U40_final/rutas_criticas.rpt`, desglosada con `scripts/desglose_ruta.py`. La peor
ruta de setup en `max_ss` (slack 51,40 ns):

| Tramo | Desde → hasta | Retardo |
|---|---|---:|
| Fetch | flanco en `_5393_` → `a_rdata_o[4]` (instrucción) | 2,01 ns |
| Decode | `a_rdata_o[4]` → `u_id.operand_b[12]` | 18,76 ns |
| Ejecución | `operand_b[12]` → ALU → `lsu_addr[31]` | 15,26 ns |
| Acceso a memoria (MMIO) | `lsu_addr[31]` → selección de periféricos → carga del contador → D de `u_cycle_counter/_281_` | 11,54 ns |
| **Retardo de datos** | | **47,56 ns** |

- **Inicio:** `_5393_`, bit 4 del registro de instrucción (salida de fetch).
- **Fin:** `u_pochoco.u_periph.u_cycle_counter/_281_` (`dffrnq_1`), un bit del contador de ciclos.
- **Etapa:** la etapa ID completa hasta el acceso a memoria. Es un `sw` al contador
  (offset `0x0C`): la ALU suma base + offset y el **bit 31** de la dirección (el último
  que calcula el sumador) decide si el acceso va a los periféricos
  (`pochoco_soc.v`). De ahí sale la señal de carga del contador, que maneja los 32
  muxes de carga.
- **Ninguna celda `dly*`** en la ruta (antes eran el 50-64 % del retardo).
- En el corner típico la peor ruta de setup es de salida (`_5339_` → `seg2_o[6]`), con
  73,95 ns de slack: las salidas tienen un retardo externo del 20 % del período en el
  SDC.

Al bajar el período y forzar el resizer, la ruta crítica se mueve: a 40 ns termina en
la RAM de datos (`u_ram.data_mem[4][1]`, un store: ALU → `lsu_addr[3]` → selección de
palabra), y a 35 ns en el register file (ALU → `lsu_addr[16]` = `alu_result[16]` →
`rf_wdata[16]` → `u_rf`).

## Barrido con la configuración anterior (con celdas `dly*`)

Primer barrido, hecho antes de excluir las celdas de retardo y de activar el DRC de
KLayout. Se conserva porque muestra el efecto de esas celdas y el problema de
estimación del resizer. Métricas en `results/timing_con_dly.csv`.

Todas las corridas de esta sección usan el mismo RTL (antes de L6) y la misma
configuración (estrategia ROM, jerarquía conservada, `FP_CORE_UTIL` = 40 %); solo
cambia lo que dice la columna "Variante". Generado con:

```bash
scripts/run_sweep.sh -d flow/asic_top -s jerarquia -p "70 60 50" -u 40
scripts/run_sweep.sh -d flow/asic_top -s rszss -p "60" -u 40 -c "PNR_CORNERS=nom_tt_025C_5v00,max_ss_125C_4v50,min_ff_n40C_5v50"
scripts/run_sweep.sh -d flow/asic_top -s margen -p "60" -u 40 -c "PL_RESIZER_SETUP_SLACK_MARGIN=14"
python3 scripts/extract_metrics.py -o results/timing_con_dly.csv flow/asic_top/runs/CP100_U40_jerarquia \
  flow/asic_top/runs/CP70_U40_jerarquia flow/asic_top/runs/CP60_U40_jerarquia \
  flow/asic_top/runs/CP50_U40_jerarquia flow/asic_top/runs/CP60_U40_rszss \
  flow/asic_top/runs/CP60_U40_margen
```

Típico = `nom_tt_025C_5v00`, más lento = `max_ss_125C_4v50` (WNS / TNS en ns). En
las 6 corridas, Magic DRC = 0, LVS = 0 y antena = 0.

| Corrida | T (ns) | Variante | Setup típico | Setup lento | Hold típico | Hold lento | Área celdas (µm²) | Celdas | ¿Cierra? |
|---|---:|---|---|---|---|---|---:|---:|---|
| `CP100_U40_jerarquia` | 100 | por defecto | 66,62 / 0 | 36,46 / 0 | 0,384 / 0 | 0,958 / 0 | 211.325 | 9.631 | sí |
| `CP70_U40_jerarquia` | 70 | por defecto | 36,62 / 0 | 6,46 / 0 | 0,384 / 0 | 0,958 / 0 | 211.325 | 9.631 | sí |
| `CP60_U40_jerarquia` | 60 | por defecto | 26,62 / 0 | **−3,54 / −440,18** | 0,384 / 0 | 0,958 / 0 | 211.325 | 9.631 | **no** |
| `CP50_U40_jerarquia` | 50 | por defecto | 17,37 / 0 | **−11,89 / −4.836,41** | 0,384 / 0 | 0,958 / 0 | 211.314 | 9.631 | **no** |
| `CP60_U40_rszss` | 60 | `PNR_CORNERS` con `max_ss` | 26,62 / 0 | **−3,54 / −440,18** | 0,384 / 0 | 0,958 / 0 | 211.325 | 9.631 | **no** |
| `CP60_U40_margen` | 60 | `PL_RESIZER_SETUP_SLACK_MARGIN = 14` | 29,67 / 0 | 2,48 / 0 | 0,384 / 0 | 0,959 / 0 | 211.218 | 9.632 | **sí** |

Con esta configuración, el menor período que cerraba era 60 ns con margen de setup en
el resizer, y 70 ns por defecto.

### Por qué la configuración por defecto no re-optimiza

(Medido con la configuración anterior; con la final pasa lo mismo, ver arriba.)

Con la configuración por defecto, el circuito de 100, 70 y 60 ns es **el mismo**: el
área y las celdas no cambian, y el slack baja exactamente lo que baja el período.
A 50 ns la diferencia es mínima (−11 µm²). El resizer de OpenROAD no encontró nada
que reparar: `RSZ-0098 No setup violations found`
(`CP60_U40_jerarquia/37-openroad-resizertimingpostcts/openroad-resizertimingpostcts.log:29`).

El motivo es que el resizer optimiza con parásitos **estimados** desde el placement,
y en este diseño esa estimación es muy optimista frente a los parásitos **extraídos**
del layout final. En `CP60_U40_rszss` (que agrega `max_ss` a los corners del STA
intermedio), el slack de setup en `max_ss` a 60 ns es:

| Etapa | Slack setup `max_ss` | Fuente |
|---|---:|---|
| Después de CTS (aquí trabaja el resizer) | +9,38 ns | `36-openroad-stamidpnr-1/ws.max.rpt:6` |
| Después del global routing | +6,29 ns | `43-openroad-stamidpnr-3/ws.max.rpt:6` |
| Signoff (SPEF extraído) | −3,54 ns | `55-openroad-stapostpnr/summary.rpt` |

Agregar el corner lento a `PNR_CORNERS` no cambia nada (`CP60_U40_rszss` es idéntica a
`CP60_U40_jerarquia`): el resizer ya veía `max_ss`, pero con +9,38 ns no tenía nada que
arreglar. Además, LibreLane solo marca como error las violaciones de los corners
`*tt*` (`TIMING_VIOLATION_CORNERS = ['*tt*']`), por eso el flujo dice "completo" aunque
`max_ss` viole.

### Re-optimización con margen (`CP60_U40_margen`)

`PL_RESIZER_SETUP_SLACK_MARGIN = 14` obliga al resizer a reparar hasta tener 14 ns de
sobra según su estimación (más que el error de estimación de unos 13 ns de la tabla
anterior). El resizer reparó los 300 endpoints (`RSZ-0099`, línea 30) cambiando el
tamaño de **11 celdas** (`RSZ-0051 Resized 11 instances: 11 up`, línea 368 de
`37-openroad-resizertimingpostcts/openroad-resizertimingpostcts.log`). Comparando los
DEF finales, son los buffers de fanout de la ruta crítica: `dlyb_1` → `dlya_1` (celda
de retardo más corta) o `clkbuf_2`. Las celdas de retardo de la ruta crítica pasan de
31,35 ns a 22,21 ns (`desglose_ruta.py`), y el slack en `max_ss` de −3,54 a +2,48 ns.
El área casi no cambia (211.325 → 211.218 µm², −0,05 %).

Esto muestra que **cada `CLOCK_PERIOD` re-optimiza el circuito solo si el resizer ve
violaciones**: el área, el buffering y el placement cambian únicamente cuando la
herramienta tiene algo que reparar. Con la estimación optimista de este diseño, a 60 ns
hizo falta un margen explícito para que eso pasara.

## Ruta crítica con la configuración anterior (L5)

(Con celdas `dly*`. La ruta de la corrida final está más arriba.)

Corrida analizada: `flow/asic_top/runs/CP100_U40_jerarquia` (T = 100 ns, U = 40 %,
estrategia de memoria ROM, jerarquía conservada para el register file, la ALU y el
contador). Fuente: `rutas_criticas.rpt` de esa corrida (las 5 peores rutas por corner,
extraídas de `55-openroad-stapostpnr/<corner>/max.rpt`). Desglose con:

```bash
python3 scripts/desglose_ruta.py flow/asic_top/runs/CP100_U40_jerarquia/rutas_criticas.rpt -c max_ss_125C_4v50
python3 scripts/desglose_ruta.py flow/asic_top/runs/CP100_U40_jerarquia/rutas_criticas.rpt -c nom_tt_025C_5v00
```

### Resultado

Las 5 peores rutas de setup, tanto en el corner típico (`nom_tt_025C_5v00`) como en el
más lento (`max_ss_125C_4v50`), recorren **la misma lógica**. Solo cambia el registro
de destino dentro del register file (`_2696_`, `_2728_`, `_2664_`, …: un bit de
distintos registros `x1`…`x15`).

| | |
|---|---|
| **Celda de inicio** | `_5387_` (`dffq_1`): bit 4 del registro de salida de la memoria de instrucciones, `u_pochoco.g_mem_rom.u_ram.a_rdata_o[4]` (`rtl/pochoco_mem_rom.v`, `a_rdata_o <= rom_data`). Es la instrucción ya leída: la salida de la etapa de fetch. |
| **Celda de fin** | `u_pochoco.u_core.u_rf/_2696_` (`dffrnq_1`): un bit de un registro del register file (`espino_register_file`) |
| **Módulos que atraviesa** | memoria de instrucciones (`pochoco_mem_rom`) → decoder y mux de operandos (`espino_id_stage`/`espino_decoder`) → ALU (`espino_alu`) → unidad de load/store (`espino_load_store_unit`) → mux de write-back (`espino_id_stage`) → `espino_register_file` |
| **Etapa de Espino** | Espino tiene dos etapas: IF (PC y lectura de la memoria de instrucciones) e ID, que en un solo ciclo hace decode, ejecución, acceso a memoria y write-back. La ruta empieza en el registro que separa IF de ID y **recorre la etapa ID completa: decode → ejecución → acceso a memoria → write-back**. |
| **Slack** | 66,62 ns en `nom_tt`, 36,46 ns en `max_ss` (cierra a 100 ns) |

### Desglose por tramos (`max_ss_125C_4v50`)

| Tramo | Desde → hasta (red del RTL) | Retardo | % |
|---|---|---:|---:|
| Fetch (clk→Q) | flanco en `_5387_` → `a_rdata_o[4]` | 1,33 ns | 2,1 % |
| **Decode** | `a_rdata_o[4]` (`opcode[4]`) → `u_id.operand_b[14]` | **28,00 ns** | 44,6 % |
| Ejecución | `operand_b[14]` → ALU → `lsu_addr[0]` (`= alu_result[0]`) | 13,44 ns | 21,4 % |
| Acceso a memoria + write-back | `lsu_addr[0]` → alineación de bytes del load → `rf_wdata[16]` | 15,16 ns | 24,1 % |
| Escritura del register file | `rf_wdata[16]` → mux de escritura → D de `u_rf/_2696_` | 4,87 ns | 7,7 % |
| **Total (retardo de datos)** | | **62,79 ns** | |

En `nom_tt` la ruta es la misma, con 32,87 ns de retardo de datos y la misma proporción
por tramo.

### Qué hace la lógica en cada tramo

1. **Decode.** `instr[4]` es un bit del opcode. Con el opcode, el decoder genera
   `alu_op_b_sel` (`OP_B_REG` para `OP` y `BRANCH`, `OP_B_IMM` para el resto,
   `espino_decoder.v:106-204`), que controla el mux de 32 bits
   `operand_b = (alu_op_b_sel == OP_B_IMM) ? imm_operand : rf_rdata_b_i`
   (`espino_id_stage.v:111`). Esa señal maneja los 32 bits del mux, y OpenROAD reparte
   el fanout con árboles de buffers (los `fanoutNNN` de la ruta).
2. **Ejecución.** La ALU calcula `alu_result`, que también es la dirección de la LSU
   (`lsu_addr_o = alu_result`, `espino_id_stage.v:128`).
3. **Acceso a memoria + write-back.** En la LSU, `boff = addr_i[1:0]` elige qué byte o
   media palabra del dato leído se devuelve (`lhalf`/`lbyte`,
   `espino_load_store_unit.v:76-86`). `rdata_o` entra al mux de write-back
   (`WD_LSU: rf_wdata_o = lsu_rdata_i`, `espino_id_stage.v:141`) y de ahí al register
   file. Por eso la ruta sale de `lsu_addr[0]`: el bit bajo de la suma de la ALU decide
   la alineación del load.

### Observaciones

- **La mitad del retardo son celdas de retardo usadas como buffers.** En la ruta hay
  9 celdas `dlyb_1` (`fanoutNNN`, `wireNNN`), que suman **31,35 ns (49,9 %)** en
  `max_ss` y 16,45 ns (50,1 %) en `nom_tt`. En todo el diseño hay 695 `dlyb_1`
  (`53-odb-cellfrequencytables/cell.rpt`). Las inserta el `repair_design` de OpenROAD
  después del placement global
  (`32-openroad-repairdesignpostgpl/openroad-repairdesignpostgpl.log`): 8 buffers de
  entrada y 19 de salida, todos `dlyb_1` (líneas 27-28), y 842 buffers en 287 redes
  para reparar 244 violaciones de slew y 209 de fanout (`MAX_FANOUT_CONSTRAINT = 10`,
  líneas 40-43). En el DEF final, los buffers `fanoutNNN` son `dlyb_1`. Una `dlyb_1`
  tarda 2,5 a 3,9 ns en `max_ss`, contra menos de 1 ns de un buffer normal. Esto
  también explica parte de las violaciones de max slew. Es un efecto de la
  herramienta, no del RTL. **Verificado:** `CP100_U40_pines` y `CP100_U40_sindly` tienen
  el mismo RTL y la misma configuración, salvo `EXTRA_EXCLUDED_CELLS =
  gf180mcu_fd_sc_mcu7t5v0__dly*` en la segunda. Al excluir las celdas de retardo, el
  setup en `max_ss` pasa de 37,56 a 54,23 ns (+16,7 ns), el retardo de datos de la ruta
  crítica de 61,51 ns (64 % en `dly*`) a 44,59 ns, y el área de celdas baja un 7,1 %
  (210.654 → 195.595 µm²). El hold sigue cerrando (0,137 → 0,134 ns), así que el repair
  de hold no necesitaba las `dlyc_1`. La corrida final usa esta exclusión.
- **La ruta es pesimista para los loads.** Un load tarda dos ciclos: la LSU detiene
  el core (`busy_q`) mientras la memoria lee. La instrucción y `addr_i[1:0]` no cambian
  entre el primer y el segundo ciclo, pero el STA analiza el camino
  instrucción → ALU → `boff` → alineación → register file como si tuviera que
  completarse en un solo ciclo.
- Con la jerarquía aplanada (`CP100_U40_prueba`) la peor ruta también empieza en la
  salida de la memoria de instrucciones (`a_rdata_o[5]`), pero los nombres internos se
  pierden y no se puede seguir por módulo. Ese es el motivo de L2.

## Optimización de la ruta crítica (L6)

### El cambio

`rtl/espino_core/espino_load_store_unit.v`: el offset de byte de un load
(`boff = addr_i[1:0]`) se registra en `boff_q` en el ciclo en que se emite el load
(`busy_d = 1`), y la alineación del dato leído (`lhalf`/`lbyte`) usa `boff_q` en vez
de `boff`.

Un load ya tardaba dos ciclos: en el primero la LSU detiene el core (`busy_o`) y la
memoria lee, y en el segundo llega el dato y se escribe en el register file. La
dirección no cambia entre los dos ciclos (la instrucción y los operandos están
congelados por el stall), así que `boff_q` en el segundo ciclo vale lo mismo que
`boff`. **No cambia la latencia ni el comportamiento**: solo saca la ALU del camino
alineación → write-back, que era el tramo "acceso a memoria + write-back" (15,2 ns) de
la ruta crítica. Costo: 2 flip-flops. Los stores no cambian (siguen usando `boff`,
porque se resuelven en un ciclo).

Se eligió este cambio frente a pre-decodificar `alu_op_b_sel` (que ataca el tramo de
decode, más largo) porque toca un solo módulo y no cambia la interfaz de las dos
memorias.

### Verificación funcional

- `sim/tb_load_store_unit.v` (nuevo): `lb`/`lbu`/`lh`/`lhu`/`lw` en todos los offsets
  de 4 palabras (bytes con y sin el bit de signo), dos loads seguidos con offsets
  distintos, y byte enables/datos de los stores. 174 chequeos contra un modelo de
  referencia escrito en el testbench. Pasa con la LSU original y con la nueva. Con una
  LSU saboteada (`boff_q` nunca se actualiza) fallan 24 chequeos: el test distingue el
  cambio. Hace falta porque el juego solo usa `lw` alineado y no ejercita la
  alineación.
- `tb_game_smoke` y `sim/run_fixed_stimuli.sh rtl rom` / `rtl ff`: salida idéntica
  byte a byte a la del RTL anterior (mismos eventos en los mismos ciclos).

### Resultado (T = 60 ns, configuración por defecto)

Esta comparación se hizo con la **configuración anterior** (con celdas `dly*`). Las dos
corridas usan la misma configuración y solo difieren en el RTL de la LSU, así que la
comparación es válida. La corrida final incluye L6.

Comparación a 60 ns, donde la versión anterior no cierra en `max_ss`. Métricas en
`results/optimizacion.csv`; violaciones de `55-openroad-stapostpnr/summary.rpt`.

| | `CP60_U40_jerarquia` (antes) | `CP60_U40_boffreg` (L6) | Cambio |
|---|---:|---:|---:|
| Setup WNS `max_ss` | −3,54 ns | −2,63 ns | +0,91 ns |
| Setup TNS `max_ss` | −440,18 ns | −21,13 ns | −95 % |
| Endpoints que violan setup en `max_ss` | 191 | 10 | −181 |
| Setup WNS `nom_tt` | 26,62 ns | 26,89 ns | +0,27 ns |
| Hold WNS peor corner | 0,139 ns | 0,117 ns | sigue ≥ 0 |
| Área de celdas | 211.325 µm² | 211.391 µm² | +66 µm² (+0,03 %) |
| Flip-flops | 1.096 | 1.098 | +2 (`boff_q`) |
| DRC / LVS / antena | 0 / 0 / 0 | 0 / 0 / 0 | |

**La ruta anterior desaparece**: ninguna de las 20 peores rutas de
`rutas_criticas.rpt` (setup y hold, `nom_tt` y `max_ss`) pasa ya por `lsu_addr`. Los
endpoints que violan bajan de 191 a 10, porque el camino alineación → write-back
llegaba a los 32 bits de los 15 registros del register file. El WNS mejora menos
(0,91 ns) porque queda otra ruta casi igual de larga, que antes estaba escondida
detrás de la primera:

| Tramo (`max_ss`) | Desde → hasta | Retardo |
|---|---|---:|
| Fetch | flanco en `_5393_` → `a_rdata_o[4]` | 2,01 ns |
| Decode | `a_rdata_o[4]` → `u_id.operand_b[17]` | 25,71 ns |
| Ejecución (comparación) | `operand_b[17]` → ALU → `u_id.alu_cmp_result` | 12,79 ns |
| Branch → PC | `alu_cmp_result` → `branch_taken` → `pc_set` → `pc_next` → D de `_5248_` | 21,26 ns |
| **Total** | | **61,77 ns** |

El fin, `_5248_`, es el bit 25 del PC (`pc_q`, `espino_if_stage.v`; su salida es
`a_addr_i[25]` de la memoria de instrucciones). La nueva ruta crítica es la de un
**branch**: decode → la ALU compara los operandos → si se toma el salto, el
`pc_target` entra al mux de next-PC de la etapa IF. 10 celdas `dlyb_1` suman 33,90 ns
(54,9 %) de la ruta. A 100 ns (la corrida final) las dos versiones cierran con mucho
margen; la mejora se ve en la frontera de los 60 ns.

### Siguiente candidato (no implementado)

El tramo más largo sigue siendo el decode (25,7 ns): `opcode` → `alu_op_b_sel` → mux de
32 bits de `operand_b`. Pre-decodificar `alu_op_b_sel` desde la salida de la ROM y
registrarlo junto con la instrucción lo sacaría de la ruta, a cambio de un puerto más
en `pochoco_mem_rom` y `pochoco_mem_ff`.
