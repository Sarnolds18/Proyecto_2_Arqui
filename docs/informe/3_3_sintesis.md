# 3.3 Síntesis

Corrida final `flow/asic_top/runs/CP100_U40_final` (T = 100 ns, U = 40 %, memoria ROM).
Fuente de las tablas: `06-yosys-synthesis/reports/stat.rpt` de esa corrida, resumido
en `results/sintesis.md` con
`python3 scripts/analisis_sintesis.py flow/asic_top/runs/CP100_U40_final -o results/sintesis.md`.

## Cómo se conservó la jerarquía

LibreLane aplana el diseño completo por defecto (`SYNTH_HIERARCHY_MODE = flatten`),
y con eso el register file, la ALU y el contador de ciclos desaparecen como módulos
del netlist. Para poder medirlos, en `flow/asic_top/config.json` se declararon esos
tres módulos en `SYNTH_KEEP_HIERARCHY_MODULES`. Yosys los sintetiza por separado
(atributo `keep_hierarchy`) y aplana todo lo demás en `asic_top`. Las instancias son:

| Módulo | Instancia |
|---|---|
| `espino_register_file` | `u_pochoco.u_core.u_rf` |
| `espino_alu` | `u_pochoco.u_core.u_id.u_alu` |
| `pochoco_cycle_counter` | `u_pochoco.u_periph.u_cycle_counter` |

El contador de ciclos estaba en el Proyecto 2 como un `always` dentro de
`pochoco_periph`. Se extrajo a su propio módulo (`rtl/pochoco_cycle_counter.v`), sin
cambiar su comportamiento, para poder identificarlo.

**Método de medición.** `06-yosys-synthesis/reports/stat.rpt` trae una sección por
módulo con la cantidad y el área **locales** (sin submódulos). La suma de las
secciones es el área total del top (`Chip area for top module`). El script
`scripts/analisis_sintesis.py` lee ese archivo y arma las tablas de abajo. En el
layout final OpenROAD aplana el netlist, pero cada celda conserva el nombre de su
instancia como prefijo (por ejemplo `u_pochoco.u_periph.u_cycle_counter/_130_`), lo
que permite ubicarlas en el layout (3.6).

**Costo de conservar la jerarquía.** Comparando `CP100_U40_prueba` (aplanado) con
`CP100_U40_jerarquia`, dos corridas iguales salvo por esta opción (anteriores a la
exclusión de las celdas `dly*` de la corrida final): el área de celdas sube un 0,2 % (210.867 → 211.325 µm²) y el
slack de setup en el corner lento baja 2,5 ns (38,98 → 36,46 ns), porque Yosys no
puede optimizar a través de los bordes de esos tres módulos. A 100 ns es un costo
despreciable.

## Área por módulo

Área de celdas después de la síntesis (antes de place & route: sin los buffers de
repair, el árbol de reloj, ni las celdas de tap y relleno).

| Módulo | Área (µm²) | % del total | Celdas | Flip-flops |
|---|---:|---:|---:|---:|
| Resto del SoC (`asic_top`, aplanado) | 77.616 | 47,4 % | 3.090 | 522 |
| `espino_register_file` | 71.588 | 43,7 % | 1.804 | 544 |
| `espino_alu` | 10.006 | 6,1 % | 580 | 0 |
| `pochoco_cycle_counter` | 4.632 | **2,8 %** | 162 | 32 |
| **Total** | **163.841** | 100 % | **5.636** | **1.098** |

- **El módulo con más área es el register file** (43,7 %). El "resto del SoC" es
  algo más grande, pero no es un módulo: es todo lo que se aplanó en el top (memoria,
  decoder, LSU, IF, periféricos, SPI, debouncer).
- **El contador de ciclos es el 2,83 % del área de celdas** (4.632 µm²): 32
  flip-flops con reset, un incrementador de 32 bits y el mux de carga para la
  escritura por MMIO.

## Las 5 celdas más usadas

| Celda | Total | Register file | ALU | Contador | Resto | Qué la explica |
|-------|-----:|-----:|-----:|-----:|-----:|----------------------------------------|
| `nand2_1` | 976 | 142 | 82 | 39 | 713 | Lógica combinacional general: decoder, mux de operandos, decodificación de direcciones y periféricos |
| `dffrnq_1` | 776 | 544 | 0 | 32 | 200 | Flip-flop con reset asíncrono. 544 del register file (15 registros × 32 bits + 2 × 32 de los registros de lectura sincrónica), 32 del contador y el resto PC, periféricos, SPI y debouncer |
| `aoi22_1` | 615 | 384 | 9 | 0 | 222 | Árboles de mux de lectura del register file (dos puertos de lectura de 16 a 1 de 32 bits) |
| `mux2_2` | 554 | 480 | 0 | 2 | 72 | Habilitación de escritura: la biblioteca no tiene flip-flops con enable (los `sdff*` son de scan y están excluidos de la síntesis en `no_synth.cells` del PDK), así que cada uno de los 480 bits del register file lleva un mux que elige entre mantener el valor o escribir `wdata` |
| `oai21_1` | 439 | 0 | 51 | 15 | 373 | Lógica combinacional general, sumadores y comparadores |


## Comparación con lo esperado

Antes de sintetizar se esperaba que el área estuviera dominada por los flip-flops, y
dentro de ellos por el register file:

- **Register file.** Se esperaban 15 × 32 = 480 flip-flops de almacenamiento (`x0`
  cableado a 0) más 64 de los registros de salida de la lectura sincrónica: 544. Es
  exactamente lo que aparece. Lo que no se había previsto es la lógica que los
  rodea: los 480 muxes de habilitación de escritura y los dos árboles de lectura.
  Por eso los flip-flops son solo el 57 % del área del módulo, y el módulo llega al
  43,7 % del total.
- **Contador de ciclos.** Con 32 de 1.098 flip-flops (2,9 %) se esperaba que fuera
  una fracción chica del área. Resultó 2,83 %, coherente: casi la mitad de su área
  son los flip-flops (51,6 % secuencial) y el resto, el incrementador.
- **ALU.** Es chica (6,1 %) porque los shifts están deshabilitados en Espino: solo
  quedan el sumador/restador, las comparaciones y las operaciones lógicas.
- **Memoria.** Con la estrategia ROM, el programa queda como lógica combinacional y
  la RAM de datos son 8 palabras de flip-flops sin reset (`dffq_1`). Ambas quedan
  dentro del "resto del SoC" (ver 3.2 para la comparación con la memoria de
  flip-flops).

## Síntesis vs. layout final

Las áreas de arriba son de la síntesis. En el layout final cada bloque crece por los
buffers que agrega el repair de OpenROAD (fanout, slew, capacitancia). La tabla de 3.6
(`docs/img/bloques.csv`, `scripts/capturas.py`) mide las mismas instancias en el
layout final:

| Bloque | Área en síntesis (µm²) | Área en el layout final (µm²) | Fracción en síntesis | Fracción del área lógica final |
|---|---:|---:|---:|---:|
| Register file | 71.588 | 82.990 | 43,7 % | 45,3 % |
| ALU | 10.006 | 13.055 | 6,1 % | 7,1 % |
| Contador de ciclos | 4.632 | 4.983 | 2,83 % | 2,7 % |

Las dos mediciones coinciden en el orden y en la fracción del contador (2,7-2,8 %). En
el layout, la memoria (ROM + RAM de datos, que en la síntesis queda dentro del "resto
del SoC") se puede separar por los nombres de sus flip-flops: es el segundo bloque más
grande (22,4 %).
