# Timing (sección 3.4)

## Barrido de `CLOCK_PERIOD` (L4)

Todas las corridas usan el mismo RTL y configuración que la corrida final
(estrategia ROM, jerarquía conservada, `FP_CORE_UTIL` = 40 %); solo cambia lo que dice
la columna "Variante". Métricas en `results/timing.csv`, generado con:

```bash
scripts/run_sweep.sh -d flow/asic_top -s jerarquia -p "70 60 50" -u 40
scripts/run_sweep.sh -d flow/asic_top -s rszss -p "60" -u 40 -c "PNR_CORNERS=nom_tt_025C_5v00,max_ss_125C_4v50,min_ff_n40C_5v50"
scripts/run_sweep.sh -d flow/asic_top -s margen -p "60" -u 40 -c "PL_RESIZER_SETUP_SLACK_MARGIN=14"
python3 scripts/extract_metrics.py -o results/timing.csv flow/asic_top/runs/CP100_U40_jerarquia \
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

**Menor período que cierra en todos los corners: 60 ns** (16,7 MHz), con margen de
setup en el resizer. Con la configuración por defecto, el menor que cierra es 70 ns.
Por debajo de 60 ns con margen: *pendiente*.

### Por qué la configuración por defecto no re-optimiza

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

## Ruta crítica (L5)

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
  herramienta, no del RTL. *Pendiente verificar*: excluir las `dly*` de los buffers
  (por ejemplo con `EXTRA_EXCLUDED_CELLS`) sin afectar el repair de hold, que usa
  `dlyc_1`.
- **La ruta es pesimista para los loads.** Un load tarda dos ciclos: la LSU detiene
  el core (`busy_q`) mientras la memoria lee. La instrucción y `addr_i[1:0]` no cambian
  entre el primer y el segundo ciclo, pero el STA analiza el camino
  instrucción → ALU → `boff` → alineación → register file como si tuviera que
  completarse en un solo ciclo.
- Con la jerarquía aplanada (`CP100_U40_prueba`) la peor ruta también empieza en la
  salida de la memoria de instrucciones (`a_rdata_o[5]`), pero los nombres internos se
  pierden y no se puede seguir por módulo. Ese es el motivo de L2.

### Candidatos para acortarla (L6)

Se decide después del barrido de períodos (L4). Hay que preferir cambios que **no
cambien el número de ciclos** del juego, para no invalidar la simulación de 3.7:

1. **Registrar `boff` en la LSU** cuando se emite el load (primer ciclo) y usar el
   valor registrado en el segundo ciclo. Así se corta el tramo
   ALU → alineación → write-back, sin cambiar la latencia. La ruta pasaría a terminar
   en `alu_result` → `rf_wdata` (WD_ALU), y lo que se gana depende de cuánto tarda el
   bit alto de la suma.
2. **Pre-decodificar `alu_op_b_sel`** a partir de `rom_data` y registrarlo junto con
   la instrucción, con el mismo enable. El mux de `operand_b` pasa a depender de un FF
   y no de la lógica de decode (el tramo más largo, 44,6 %). Requiere un puerto extra
   en las dos memorias (`pochoco_mem_rom` y `pochoco_mem_ff`).
