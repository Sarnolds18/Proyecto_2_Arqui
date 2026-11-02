# 3.4 Timing

Detalle completo, comandos y archivo:línea de cada número en `docs/timing.md`. Métricas
en `results/timing.csv` (configuración final), `results/timing_con_dly.csv`
(configuración anterior) y `results/optimizacion.csv` (L6).

## Corners

LibreLane analiza 9 corners: parásitos `nom`/`min`/`max` × `tt_025C_5v00`,
`ss_125C_4v50` y `ff_n40C_5v50`. En las tablas, **típico = `nom_tt_025C_5v00`** y
**más lento = `max_ss_125C_4v50`** (proceso lento, 125 °C, 4,5 V y parásitos máximos).
El peor hold aparece en los corners `ff` (0,13-0,14 ns en todas las corridas, siempre
positivo).

## Barrido de `CLOCK_PERIOD`

Configuración de la corrida final (memoria ROM, sin celdas de retardo, `FP_CORE_UTIL` =
40 %). WNS / TNS en ns. En todas las corridas, Magic DRC = 0, KLayout DRC = 0, LVS
limpio y antena = 0.

| T (ns) | Variante | Setup típico | Setup lento | Hold típico | Hold lento | Área (µm²) | ¿Cierra? |
|---:|---|---|---|---|---|---:|---|
| 100 | por defecto (**corrida final**) | 73,95 / 0 | 51,40 / 0 | 0,390 / 0 | 0,970 / 0 | 196.097 | sí |
| 60 | por defecto | 34,03 / 0 | 11,40 / 0 | 0,390 / 0 | 0,970 / 0 | 196.097 | sí |
| 50 | por defecto | 24,03 / 0 | 1,40 / 0 | 0,390 / 0 | 0,970 / 0 | 196.097 | sí |
| 40 | por defecto | 14,03 / 0 | **−8,60 / −1.928,45** | 0,390 / 0 | 0,970 / 0 | 196.097 | **no** |
| 40 | margen de setup de 14 ns | 20,58 / 0 | 3,55 / 0 | 0,390 / 0 | 0,970 / 0 | 197.320 | sí |
| 35 | margen de setup de 14 ns | 19,60 / 0 | 6,09 / 0 | 0,391 / 0 | 0,971 / 0 | 204.154 | sí |
| 30 | margen de setup de 14 ns | 14,70 / 0 | 1,28 / 0 | 0,390 / 0 | 0,971 / 0 | 203.960 | sí |

**El menor período probado que cierra en todos los corners es 30 ns (33,3 MHz)**, con
margen de setup en el resizer; con la configuración por defecto es **50 ns (20 MHz)**.
No se probó nada por debajo de 30 ns, pero el límite parece cercano: de 35 a 30 ns el
retardo de la ruta crítica casi no baja (27,91 → 27,71 ns).

**Cada `CLOCK_PERIOD` re-optimiza el circuito, pero solo si el resizer de OpenROAD ve
violaciones.** Con la configuración por defecto, de 100 a 40 ns el circuito es el mismo
(196.097 µm², 9.651 celdas) y el slack baja exactamente lo que baja el período. El
resizer reporta `RSZ-0098 No setup violations found` incluso a 40 ns, donde el signoff
encuentra 498 endpoints violando. El motivo es que optimiza con parásitos **estimados**
desde el placement, que en el corner lento son mucho más optimistas que los
**extraídos** del layout final. Medido a 60 ns con la configuración anterior: el
resizer estimaba +9,38 ns, el signoff dio −3,54 ns.

`PL_RESIZER_SETUP_SLACK_MARGIN = 14` le exige 14 ns de sobra según su estimación, y ahí
sí trabaja. Cuanto más corto el período, más cambia el circuito:

| | 40 ns con margen | 35 ns con margen | 30 ns con margen |
|---|---:|---:|---:|
| Endpoints reparados | 787 | 898 | 908 |
| Celdas agrandadas | 175 | 693 | 679 |
| Buffers insertados | 3 | 53 | 54 |
| Área vs. corrida final | +0,6 % | +4,1 % | +4,0 % |
| Retardo de datos de la ruta crítica (`max_ss`) | 35,28 ns | 27,91 ns | 27,71 ns |

Además, LibreLane solo marca como error las violaciones de los corners típicos
(`TIMING_VIOLATION_CORNERS = ['*tt*']`), así que el flujo termina "completo" aunque el
corner lento viole. El criterio de cierre de las tablas se revisa en los 9 corners con
`scripts/extract_metrics.py`.

### Celdas de retardo

En las primeras corridas, la mitad del retardo de la ruta crítica eran celdas `dlyb_1`:
el `repair_design` de OpenROAD las usaba como buffers de fanout (695 en todo el
diseño), y cada una tarda 2,5 a 3,9 ns en el corner lento. La corrida final las excluye
(`EXTRA_EXCLUDED_CELLS`). Con el mismo RTL y la misma configuración, salvo esa opción
(`CP100_U40_pines` vs. `CP100_U40_sindly`):

| | Con `dly*` | Sin `dly*` |
|---|---:|---:|
| Setup WNS lento (T = 100 ns) | 37,56 ns | 54,23 ns |
| Retardo de datos de la ruta crítica | 61,51 ns (64 % en `dly*`) | 44,59 ns |
| Área de celdas | 210.654 µm² | 195.595 µm² (−7,1 %) |
| Hold peor | 0,137 ns | 0,134 ns |

Con las `dly*`, el período mínimo era 70 ns por defecto y 60 ns con margen.

## Ruta crítica de la corrida final

`CP100_U40_final`, corner `max_ss`, slack 51,40 ns:

| | |
|---|---|
| Celda de inicio | `_5393_` (`dffq_1`): bit 4 del registro de salida de la memoria de instrucciones, es decir, la instrucción ya leída (fin de la etapa de fetch) |
| Celda de fin | `u_pochoco.u_periph.u_cycle_counter/_281_` (`dffrnq_1`): un bit del contador de ciclos |
| Módulos | memoria de instrucciones → decoder y mux de operandos (`espino_id_stage`) → `espino_alu` → decodificación de direcciones del SoC → `pochoco_periph` → `pochoco_cycle_counter` |
| Etapa de Espino | Espino tiene dos etapas: IF y una ID que en un ciclo hace decode, ejecución, acceso a memoria y write-back. Esta ruta recorre la ID desde el **decode** hasta el **acceso a memoria** (un store al contador) |

| Tramo | Desde → hasta | Retardo |
|---|---|---:|
| Fetch | flanco de reloj → `a_rdata_o[4]` | 2,01 ns |
| Decode | `opcode` → mux de `operand_b` | 18,76 ns |
| Ejecución | ALU → `lsu_addr[31]` | 15,26 ns |
| Acceso a memoria | bit 31 de la dirección → selección de periféricos → carga del contador | 11,54 ns |
| **Total** | | **47,56 ns** |

Es la ruta de un `sw` al contador (offset `0x0C`): la ALU suma base + offset, y el
**bit 31** de la dirección, el último que resuelve el sumador, decide si el acceso va a
los periféricos. De ahí sale la señal de carga del contador. En el corner típico la
peor ruta es de salida (registro → `seg2_o[6]`, slack 73,95 ns), porque el SDC le asigna
a las salidas un retardo externo del 20 % del período.

## Optimización de la ruta crítica

Con la configuración anterior, la ruta crítica iba de la instrucción al register file
pasando por la **alineación de los loads**: el byte offset (`addr[1:0]`, que sale de la
ALU) elegía qué byte del dato leído se escribía en el register file.

**Cambio** (`rtl/espino_core/espino_load_store_unit.v`): el offset se guarda en un
registro de 2 bits (`boff_q`) en el ciclo en que se emite el load, y la alineación usa
ese registro. Un load ya tardaba dos ciclos (la LSU detiene el core mientras la memoria
lee) y la dirección no cambia entre ellos, así que **la latencia y el comportamiento no
cambian**: solo se saca la ALU del camino alineación → write-back. Se verificó con un
testbench nuevo (`sim/tb_load_store_unit.v`, 174 chequeos de todos los loads en todos
los offsets; con una LSU saboteada fallan 24), y las simulaciones del juego dan
idénticas byte a byte.

**Resultado** (T = 60 ns, configuración anterior, misma configuración en ambas):

| | Antes | Con el cambio | Diferencia |
|---|---:|---:|---:|
| Setup WNS lento | −3,54 ns | −2,63 ns | +0,91 ns |
| Setup TNS lento | −440,18 ns | −21,13 ns | −95 % |
| Endpoints que violan | 191 | 10 | −181 |
| Área de celdas | 211.325 µm² | 211.391 µm² | +0,03 % (+2 FF) |

La ruta atacada desaparece y las violaciones bajan de 191 a 10. El WNS mejora poco
porque debajo había otra ruta casi igual de larga, la de los **branches**: decode → la
ALU compara los operandos → `branch_taken` → mux de next-PC → registro del PC (etapa
IF). Con la configuración final, sin celdas de retardo, la ruta crítica pasó a ser el
store al contador descrito arriba. El siguiente paso sería pre-decodificar
`alu_op_b_sel` junto con la instrucción, para sacar el decode (el tramo más largo en
todas estas rutas) del camino.

## Constantes de `game.s` para el período T

El juego mide el tiempo en ciclos con el contador, así que cada constante de tiempo es
`segundos × f`, con `f = 1 / T`. Se carga con `lui` (20 bits altos) + `addi` (12 bits
bajos con signo). Si el bit 11 es 1, el `addi` queda negativo y el `lui` sube en 1.

| Constante | T = 100 ns, f = 10 MHz (corrida final) | T = 30 ns, f = 33,33 MHz (menor período probado que cierra) |
|---|---|---|
| 3 s | 30.000.000 = `0x01C9C380` → `lui 0x1C9C` + `addi 896` | 100.000.000 = `0x05F5E100` → `lui 0x5F5E` + `addi 256` |
| 2 s | 20.000.000 = `0x01312D00` → `lui 0x1313` + `addi -768` | 66.666.667 = `0x03F940AB` → `lui 0x3F94` + `addi 171` |
| 0,1 s | 1.000.000 = `0x000F4240` → `lui 0xF4` + `addi 576` | 3.333.333 = `0x0032DCD5` → `lui 0x32E` + `addi -811` |

A 100 ns las constantes son exactas y son las de `sw/game.s`. A 30 ns, la de 3 s es exacta
y las otras dos no son enteras y se redondean: el error es de 0,33 ciclos (≤ 1 × 10⁻⁷ relativo),
despreciable frente a la décima de segundo que muestra el juego. Para usar otro período
se cambian estas tres constantes en `sw/game.s` y se regenera el programa con
`python3 -B sw/assembler.py sw/game.s sw/game.hex --rom rtl/game_rom.v`.
