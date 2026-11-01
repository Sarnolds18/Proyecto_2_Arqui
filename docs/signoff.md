# Signoff y layout (3.6)

Corrida final: `flow/asic_top/runs/CP100_U40_final` (T = 100 ns, `FP_CORE_UTIL` = 40 %,
memoria ROM, LibreLane 3.0.16, `gf180mcuD` rev. `54435919…`). Die 653,44 × 671,36 µm
(0,4387 mm²). Todos los números salen de los reportes de esa carpeta; la ruta de cada
uno está en la tabla.

## Resumen

| Chequeo | Resultado | Reporte |
|---|---|---|
| DRC Magic | **0** | `64-magic-drc/reports/drc.magic.rpt` |
| DRC KLayout (558 reglas) | **0** | `65-klayout-drc/reports/drc.klayout.json`, `final/metrics.json` (`klayout__drc_error__count`) |
| XOR Magic vs. KLayout (GDS) | **0** diferencias | `final/metrics.json` (`design__xor_difference__count`) |
| LVS (Netgen) | **"Circuits match uniquely"** | `70-netgen-lvs/reports/lvs.netgen.rpt` |
| Antena (final, tras ruteo detallado) | **0** redes / 0 pines | `46-openroad-checkantennas-1/reports/antenna_summary.rpt` |
| Setup / hold, 9 corners | WS ≥ 0, TNS = 0 (peor setup 51,40 ns en `max_ss`, peor hold 0,143 ns en `min_ff`) | `55-openroad-stapostpnr/summary.rpt` |
| IR drop (VDD) | peor 0,143 mV, promedio 0,026 mV | `56-openroad-irdropreport/irdrop.rpt` |
| Max slew / cap / fanout | 2.867 / 10 / 68 (fuera del criterio, ver abajo) | `55-openroad-stapostpnr/summary.rpt`, `max_ss_125C_4v50/checks.rpt` |

`76-misc-reportmanufacturability/manufacturability.rpt`: Antenna, LVS y DRC "Passed".

## DRC: Magic y KLayout

Con `gf180mcuD`, LibreLane trae `KLAYOUT_DRC_RUNSET` sin definir y **salta el DRC de
KLayout**: en las primeras corridas (PM32, `CP100_U40_prov`, barridos) el "DRC Passed"
venía solo de Magic. El PDK sí trae el runset (`libs.tech/klayout/tech/drc/gf180mcu.drc`),
así que se habilitó en `flow/asic_top/config.json`:

- `KLAYOUT_DRC_RUNSET = pdk_dir::libs.tech/klayout/tech/drc/gf180mcu.drc`
- `KLAYOUT_DRC_DEFINES`: `metal_top = 11K`, `mim_option = B`, `metal_level = 5LM` (la
  variante D del PDK), `feol`, `beol`, `offgrid` y `conn_drc` activados, `run_mode = deep`.

En la corrida final ejecuta 558 reglas en 4 min 19 s (`65-klayout-drc/runtime.txt`) y
reporta 0 violaciones. Magic también da 0. Son dos herramientas independientes sobre el
mismo GDS, y el XOR entre el GDS de Magic y el de KLayout da 0 diferencias.

## LVS

Netgen compara el netlist extraído del layout (Magic) contra el netlist de PnR:
`Final result: Circuits match uniquely.` Las celdas de antena (diodos) aparecen en ambos
lados como `gf180mcu_fd_sc_mcu7t5v0__antenna`.

## Antena

### Violaciones que aparecieron y se corrigieron en la corrida final

Después del ruteo global, `40-openroad-checkantennas` encontró **4 redes que violan la
regla de antena** (razón de área lateral máxima 400):

| Red | Pin afectado | Capa | Razón / requerida | P/R | Ubicación del pin (µm) | Qué es |
|---|---|---|---|---|---|---|
| `_1972_` | `fanout29/I` | Metal2 | 633,66 / 400 | 1,58 | (393,7; 619,4), borde norte | salida de una `nor2_1` de lógica del core |
| `u_pochoco.u_core.u_rf/_1239_` | `u_rf/fanout296/I` | Metal2 | 446,64 / 400 | 1,12 | (232,4; 290,1), dentro del register file | salida de una `nand2_1` del mux de lectura del register file |
| `net224` | `fanout223/I` | Metal2 | 406,35 / 400 | 1,02 | (525,8; 152,9), zona de la memoria | rama de un árbol de buffers de fanout |
| `net893` | `fanout878/I` | Metal4 | 402,02 / 400 | 1,01 | (348,9; 168,6), centro-sur | **red de reset** (`u_pochoco.rst_ni` → `fanout893` → …) |

Fuente: `40-openroad-checkantennas/reports/antenna_summary.rpt`. Ubicaciones:
`final/def/asic_top.def` (unidades de 1/2000 µm).

**Por qué aparecen**: durante la fabricación, un tramo largo de metal conectado solo a
la compuerta de un transistor acumula carga en el grabado por plasma. Si el área del
metal es mucho mayor que el área de compuerta, esa carga puede romper el óxido de
compuerta. Las 4 redes son tramos largos de Metal2/Metal4 que llegan a la entrada de un
`buf_1`, que tiene una compuerta chica.

**Cómo se resolvió** (`42-openroad-repairantennas/1-openroad-diodeinsertion/`,
`repair_antennas` con 3 iteraciones y 10 % de margen):

1. 4 violaciones → 3 **jumpers** en 3 redes. Un jumper corta el tramo largo y lo sube
   brevemente a una capa superior, para que la compuerta quede conectada a menos metal
   mientras se fabrican las capas inferiores. Queda 1 violación.
2. 1 violación → 1 **diodo de antena** (`gf180mcu_fd_sc_mcu7t5v0__antenna`). El diodo
   descarga a sustrato la carga del metal. Al reubicar, aparecen 2 violaciones nuevas.
3. 2 violaciones → 2 jumpers en 2 redes → **0**.

El chequeo posterior al repair (`42-…/2-openroad-checkantennas`) y el chequeo final
después del ruteo detallado (`46-openroad-checkantennas-1`) dan 0 redes y 0 pines. El
netlist final tiene 3 celdas `__antenna`.

### Ejemplo de violación que no se pudo corregir: memoria de flip-flops

En la corrida de la estrategia 2 de memoria (`flow/asic_top_ff/runs/CP100_U40_ff`), el
diseño es ~4 veces más grande (die 1.244 × 1.262 µm) y el ruteo mucho más congestionado:

| Etapa | Redes / pines con violación | Fuente |
|---|---|---|
| Tras ruteo global (`40-openroad-checkantennas`) | 125 / 132 | `openroad-checkantennas.log` |
| Repair (`42-openroad-repairantennas`) | 159 → 108 → 91 → 12 → 5 → 3 → 0, con 157 jumpers y 145 diodos | `1-openroad-diodeinsertion/*.log` (`GRT-0012/0302/0015`) |
| Tras ruteo detallado (`46-openroad-checkantennas-1`) | **1 / 1** | `reports/antenna_summary.rpt` |

La violación que queda es `net4125` → `fanout4124/I` (una `dlyb_1`), Metal2,
472,61 / 400 (P/R 1,18), con el pin en (968,2; 109,8) µm, cerca del borde sur. El repair
de antenas trabaja sobre el ruteo **global**, y el ruteo detallado posterior cambió el
recorrido de esa red y volvió a dejar un tramo largo de Metal2. Por eso esa corrida **no
cierra** con el criterio del enunciado. Formas de corregirla, que no se aplicaron porque
la estrategia elegida fue la ROM: subir `GRT_ANTENNA_REPAIR_MARGIN` para que el repair
deje más holgura, activar el repair de antena después del ruteo detallado, o insertar un
diodo a mano en ese pin.

## Violaciones eléctricas fuera del criterio (slew, capacitancia, fanout)

El criterio del enunciado es DRC, LVS, antena y setup/hold. LibreLane reporta además
violaciones de **max slew** (transición > `MAX_TRANSITION_CONSTRAINT` = 3 ns),
**max cap** y **max fanout** (`MAX_FANOUT_CONSTRAINT` = 10), pero no las trata como error
(`MAX_SLEW_VIOLATION_CORNERS` y `MAX_CAP_VIOLATION_CORNERS` vacíos en `resolved.json`).
No afectan el cierre, pero se explican aquí.

| Corner | Max slew | Max cap |
|---|---:|---:|
| `nom_tt_025C_5v00` (típico) | 21 | 4 |
| `max_tt_025C_5v00` | 223 | 9 |
| `min_ss_125C_4v50` | 1.739 | 3 |
| `nom_ss_125C_4v50` | 2.293 | 4 |
| `max_ss_125C_4v50` (más lento) | **2.867** | **10** |
| corners `ff` | 0–10 | 3–9 |

Fuente: `55-openroad-stapostpnr/summary.rpt`.

**Por qué**: `repair_design` (etapa 32) dimensiona buffers en el corner por defecto
(`DEFAULT_CORNER = nom_tt_025C_5v00`) con un 20 % de margen
(`DESIGN_REPAIR_MAX_SLEW_PCT = 20`), es decir, apunta a transiciones de hasta ~2,4 ns
en tt. En ss (125 °C, 4,5 V) las mismas celdas son más lentas y esas transiciones pasan
de 3 ns. Por eso en tt quedan solo 21 violaciones y en `max_ss` 2.867.

**Dónde**: `python3 scripts/slew_por_bloque.py flow/asic_top/runs/CP100_U40_final`
clasifica cada pin de `max_ss_125C_4v50/checks.rpt` según la red que lo excita. Ese
reporte lista 2.935 pines, mientras que `summary.rpt` informa 2.867. No se investigó de
dónde sale la diferencia de 68.

| Bloque | Pines |
|---|---:|
| Register file (redes internas de `u_rf`, selects de los mux de lectura de 15×32 bits) | 1.435 |
| Resto del core (`pc_id`, `rf_wdata`, `lsu_addr`, …) | 1.083 |
| Red de reset (`u_pochoco.rst_ni` y sus 105 redes de buffers) | 234 |
| ALU | 146 |
| Memoria | 37 |

El peor pin es `fanout878/I`, con 7,08 ns contra un límite de 3 ns. Está en la **red de
reset**, la misma red (`net893`) que tuvo una de las 4 violaciones de antena: un árbol de
buffers `buf_1` (la celda más débil) que reparte el reset a los flip-flops.

**Qué implica**: el STA calcula setup/hold con esas transiciones, y aun así hay 51 ns de
slack en `max_ss`. Como están fuera del rango de 3 ns para el que se garantiza la
biblioteca, esos retardos son menos confiables. Una
transición lenta significa más consumo de corto circuito y más sensibilidad a ruido. En
la red de reset solo afecta la liberación del reset, que es sincrónica (sincronizador de
2 FF) y se verifica con los chequeos de recovery/removal, que pasan.

**Intento de corregirlo**: se probó `DESIGN_REPAIR_MAX_SLEW_PCT = 60` (y lo mismo para
GRT) para que el repair dejara más margen. Dos corridas (`CP100_U40_signoff` y
`CP100_U40_signoff2`) quedaron detenidas en la etapa 32 (`repairdesignpostgpl`) sin
escribir nada en el log, cuando sin ese cambio la etapa tarda menos de 1 minuto. Se
abandonaron y se borraron porque no tenían métricas. La alternativa sería hacer el repair
en el corner lento (`PNR_CORNERS`), lo que agrega buffers y área.

## Layout anotado

`docs/img/layout_anotado.png` (render del GDS final con KLayout y celdas coloreadas por
bloque), `docs/img/bloques.png` (solo las celdas de cada bloque) y
`docs/img/bloques.csv`. Generados con:

```bash
python3 scripts/capturas.py flow/asic_top/runs/CP100_U40_final -o docs/img
```

| Bloque | Instancia | Celdas | FF | Área (µm²) | % del área lógica |
|---|---|---:|---:|---:|---:|
| Register file | `u_pochoco.u_core.u_rf` | 2.517 | 544 | 82.990 | 45,3 % |
| Memoria (ROM + RAM de datos) | `u_pochoco.g_mem_rom.u_ram` | 1.623 | 319 | 41.070 | 22,4 % |
| ALU | `u_pochoco.u_core.u_alu` | 787 | 0 | 13.055 | 7,1 % |
| Contador de ciclos | `u_pochoco.u_periph.u_cycle_counter` | 197 | 32 | 4.983 | 2,7 % |

El área lógica (183.053 µm²) excluye las celdas físicas (relleno, taps, diodos). Contra
el área total de celdas estándar (196.097 µm², `design__instance__area__stdcell`), el
contador es el 2,5 %.

**Cómo se identifica cada bloque**: el netlist final está aplanado, pero
`SYNTH_KEEP_HIERARCHY_MODULES` (register file, ALU, contador) hace que sus celdas
conserven el prefijo de instancia (`u_rf/…`, `u_alu/…`, `u_cycle_counter/…`). Para la
memoria se usa el nombre de la red Q de cada flip-flop y el cono de lógica exclusivo
(detalle en la cabecera de `scripts/capturas.py`).

**Qué se ve**: el register file ocupa casi toda la mitad oeste. La ALU queda en el
centro, entre el register file (que le entrega los operandos) y la memoria. El contador
está debajo de la ALU. La memoria se reparte en dos zonas, noreste y sur, separadas por
la ALU.
