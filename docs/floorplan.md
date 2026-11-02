# 3.5 Floorplan, alimentación, placement y costo

Corridas de `flow/asic_top` (estrategia de memoria ROM, `CLOCK_PERIOD` = 100 ns) con
los pines por función de `flow/asic_top/pin_order.cfg`, variando solo `FP_CORE_UTIL`.

```bash
scripts/run_sweep.sh -s final -p "100" -u "40 50 60 70 75 80"
python3 scripts/floorplan.py -o results/floorplan.csv -g results/floorplan.png \
  flow/asic_top/runs/CP100_U*_final
```

RTL y configuración de la corrida final (`CP100_U40_final` es el punto de 40 %). U40–U70
salen del commit `0d4c807`; U75 y U80 se lanzaron después del pull de `3de727d`, que solo
cambia `pochoco_mem_ff.v`, un módulo que la estrategia ROM no instancia (no entra al
netlist).

El barrido anterior (`CP100_U*_pines`, RTL y config del 1/11 a mediodía, con celdas
`dly*`) cerraba hasta 70 % y fallaba a 75 %. Se conserva como dato histórico.

## Terminales del macro

| Lado | Terminales | Por qué ahí |
|---|---|---|
| Oeste | `rst_ni`, `clk_i` | Señales globales, solas en un lado: la raíz del árbol de reloj parte del borde sin compartirlo con buses de datos, y el reset entra junto al reloj al sincronizador de `pochoco_soc` |
| Sur | `btn_i[3:0]`, `led_o[3:0]` | La interfaz de usuario: los dos buses terminan en el mismo bloque (`pochoco_periph`: `debounce_bank` y registro de LEDs), así que conviene que entren juntos |
| Norte | `seg1_o[6:0]`, `seg2_o[6:0]` | El bus más ancho (14 salidas) con un lado propio, cada display con sus 7 segmentos contiguos y en orden, para que quien integre el macro los rutee sin cruces |
| Este | `spi_cs_ni`, `spi_sclk_i`, `spi_mosi_i`, `spi_miso_o` | Interfaz independiente (`pochoco_spi_slave`), separada del resto |

`ERRORS_ON_UNMATCHED_IO = both`: el flujo se detiene si un puerto no aparece en el
archivo o si el archivo nombra un puerto que no existe.

**Terminales de macro vs. pads de I/O.** Estos terminales son solo rectángulos de metal
en el borde (Metal2 en los lados norte/sur, Metal3 en este/oeste, `IO_PIN_V_LAYER`/
`IO_PIN_H_LAYER`), sin circuitos: los maneja directamente una celda estándar del macro.
En un chip completo cada señal pasaría por una celda de pad (`gf180mcu_fd_io`) con
protección ESD, buffers de salida capaces de cargar una pista de PCB y un bondpad, más
pads de alimentación, todos en un anillo alrededor del core. Ese anillo ocupa mucho más
que este macro entero y fija el orden de los pines según el encapsulado, no según la
lógica.

## Barrido de utilización

| `FP_CORE_UTIL` | Die (µm) | Die (mm²) | Util. final | Uso ruteo global | Violaciones DRT iter. 0 | Setup WS ss (ns) | Hold WS peor (ns) | ¿Cierra? | Costo (US$) |
|---|---|---|---|---|---|---|---|---|---|
| 40 % | 653,4 × 671,4 | 0,4387 | 48,0 % | 23,34 % | 51 | 51,40 | 0,143 | sí | 10.090 |
| 50 % | 585,9 × 603,8 | 0,3537 | 59,0 % | 26,91 % | 3.146 | 53,37 | 0,120 | sí | 8.136 |
| 60 % | 536,0 × 553,9 | 0,2969 | 70,2 % | 30,54 % | 56 | 52,89 | 0,138 | sí | 6.829 |
| 70 % | 497,2 × 515,2 | 0,2562 | 81,6 % | 34,97 % | 57 | 51,88 | 0,120 | sí | 5.892 |
| **75 %** | **480,8 × 498,8** | **0,2398** | 86,9 % | 39,06 % | 2.742 | 51,25 | 0,124 | **sí** | **5.516** |
| 80 % | — | — | — | — | — | — | — | no: el flujo no termina | — |

Fuente: `results/floorplan.csv`. "Util. final" es la utilización después de buffering y
CTS (`design__instance__utilization`), mayor que el `FP_CORE_UTIL` pedido porque después
del floorplan el flujo agrega buffers de repair, el árbol de reloj y la corrección de
hold. En todas las que cierran: DRC Magic 0, DRC KLayout 0, LVS 0, antena 0, setup y hold
con WS ≥ 0 y TNS = 0 en los 9 corners.

![Barrido de utilización](../results/floorplan.png)

**Área mínima que cierra: `FP_CORE_UTIL` = 75 %, die de 0,2398 mm².** A 80 % el flujo
se detiene en CTS, antes de rutear: no queda espacio para legalizar las celdas que se
insertan después del placement.
`flow/asic_top/runs/CP100_U80_final/35-openroad-cts/openroad-cts.log:109` (`DPL-0034`,
10 instancias sin lugar, 3 del register file) y `:120` (`DPL-0036 Detailed placement
failed`).

**Congestión.** El uso de recursos del ruteo global crece de forma monótona con la
utilización, de 23 % a 39 %: es la métrica de congestión más limpia del barrido. Las
violaciones tras la primera iteración del ruteo detallado **no** son monótonas (51, 3.146,
56, 57, 2.742). Dependen de cómo quedó el placement en cada punto, y el ruteador las
lleva a 0 en todas las corridas que terminan. Solo indican cuánto trabajo extra tuvo el
ruteador, no un límite.

**Qué limita.** El timing casi no cambia (setup ss entre 51 y 53 ns en todos los
puntos, porque a 100 ns sobra holgura) y el ruteo siempre termina limpio. El límite lo
pone el **espacio para legalizar celdas**: a 80 % el placement inicial cabe, pero las
celdas que agrega CTS ya no encuentran lugar.

**Respecto del barrido anterior** (`_pines`): ahora cierra también a 75 %. La
explicación más probable es la exclusión de las celdas `dly*`. `repair_design` usaba
`dlyb_1` como buffers de fanout, y una `dlyb_1` mide 8,96 × 3,92 µm, contra
3,36 × 3,92 µm de un `buf_1` (LEF de la biblioteca), o sea 2,7 veces el área. Sin ellas,
las celdas que se agregan después del placement ocupan menos y CTS encuentra lugar a 75 %.
El área de celdas antes del repair es casi igual en los dos barridos (164.629 contra
163.841 µm², `*-openroad-floorplan/state_out.json`). La diferencia aparece en lo que se
agrega después: en la corrida de prueba `CP100_U40_sindly`, el área final bajó 7 %.

## Costo

Con US$23.000/mm² escalando linealmente con el área del die:

- Corrida exigida (U = 40 %): 0,4387 mm² → **US$10.090**.
- Área mínima que cierra (U = 75 %): 0,2398 mm² → **US$5.516** (−45 %).

Limitaciones de la aproximación:
- Es solo el macro: un chip real necesita el anillo de pads, que para un diseño tan
  chico ocupa más área que el core (el die quedaría limitado por los pads, no por la
  lógica).
- El costo real no es lineal: hay costos fijos (máscaras, diseño, verificación) que no
  dependen del área, y en un shuttle multiproyecto se compra un slot de tamaño mínimo.
- No incluye rendimiento (yield): la probabilidad de un defecto crece con el área, y
  tampoco el corte del wafer, encapsulado ni test.
- Es para un nodo y un proceso fijos (GF180MCU); no sirve para extrapolar a otro nodo.

**Decisión que más pesó en el área.** Dimensionar la memoria al uso real del juego. Con
la RAM de 512 palabras del Proyecto 2 la síntesis ya daba 2,31 mm² solo de celdas
(`flow/asic_top/runs/01_regfile_ff`, ver `docs/evidencia.md` #3), contra 0,196 mm²
de celdas con la ROM en la corrida final (≈ 12 veces menos). La utilización vino
después y solo mueve el die dentro de un factor ~1,8 (0,439 → 0,240 mm²). Comparación con la estrategia de
flip-flops: ver `docs/memoria.md`.
