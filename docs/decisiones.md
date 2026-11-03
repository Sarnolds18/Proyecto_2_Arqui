# Decisiones del Proyecto 3

Registro de las decisiones de diseño y de flujo, con su motivo. El detalle técnico de
cada una está en el doc enlazado; este archivo sirve para ubicarlas rápido (informe y
defensa). Fechas de 2026.

## Repositorio y flujo de trabajo

| Decisión | Por qué | Quién / cuándo | Detalle |
|---|---|---|---|
| El P3 vive en la rama `proyecto3` del repo del P2; la entrega del P2 queda marcada con el tag anotado `p2-entrega` (`bb042a1`) | El enunciado exige partir del repo entregado en el P2; así `main` no se toca hasta el final | Santiago, 26/10 | — |
| La rama `proyecto3` **no** se mantiene sintetizable para la Go Board | El enunciado no lo pide, y con el register file de flip-flops `game_top` ya no cabe en la iCE40 HX1K (Yosys: 1.872 LUT contra 1.280 celdas lógicas). La versión para la placa es el tag `p2-entrega` | Santiago, 30/10 | `README.md` |
| LibreLane fijado en el tag **3.0.16**; PDK `gf180mcuD` revisión `54435919…` (la que instala esa versión) | Que todas las corridas del informe usen las mismas herramientas en cualquier máquina | Santiago, 30/10 | `docs/instalacion.md`, `README.md` |
| Una carpeta por corrida con tag descriptivo (`CP<T>_U<U>_<sufijo>`), **nunca sobrescribir**; barridos con `scripts/run_sweep.sh`, que salta los tags que ya existen | Cada número del informe tiene que poder rastrearse hasta una corrida guardada | Santiago, 30/10 | `scripts/run_sweep.sh` |
| Se versionan logs, `.rpt`, `metrics.json` y `resolved.json`, pero **no** los `max/min.rpt` de STA post-PnR ni los reportes de STA intermedios; `scripts/extract_critical_paths.py` guarda las 5 peores rutas en `<corrida>/rutas_criticas.rpt` | Una corrida completa pesaba 43 MB (40 MB de esos reportes); con el filtro pesa ~3 MB. Las rutas críticas siguen disponibles para 3.4 | Santiago, 30/10 | `.gitignore` |
| Métricas a CSV con `scripts/extract_metrics.py` (setup/hold en corner típico, lento y el peor de los 9, área, DRC, LVS, antena) | Tablas del informe reproducibles; criterio de "cierra" calculado igual para todas las corridas | Santiago, 30/10 | `results/*.csv` |
| Corners del informe: típico = `nom_tt_025C_5v00`, más lento = `max_ss_125C_4v50` | LibreLane corre 9 corners (parásitos nom/min/max × tt/ss/ff); el enunciado pide el típico y el más lento | Santiago, 26/10 | `scripts/extract_metrics.py` |

## RTL: de FPGA a ASIC (3.1)

| Decisión | Por qué | Quién / cuándo | Detalle |
|---|---|---|---|
| Correr LibreLane con el RTL del P2 **antes de arreglar nada** y guardar esas corridas (`00`, `01`, `02`) | El enunciado pide el log y la línea que evidenciaron cada construcción | Santiago, 26–30/10 | `docs/evidencia.md` |
| Register file reescrito con 15 × 32 flip-flops (x0 cableado a 0), **manteniendo la lectura sincrónica** y con reset a 0 | `SB_RAM40_4K` no existe en la biblioteca. El core depende de la latencia de un ciclo de la BRAM (FSM `ops_valid_q` de `espino_id_stage.v`), y el reset reproduce el `INIT_0 = 0` de la BRAM | Santiago, 30/10 | `docs/evidencia.md` #1 |
| Reset externo `rst_ni` (activo bajo) en `asic_top`, con un **sincronizador de 2 FF dentro de `pochoco_soc`** (aserción asíncrona, liberación sincrónica); se eliminó `por_cnt` | En silicio los FF arrancan indeterminados y el valor inicial de `por_cnt` se pierde en síntesis. El sincronizador queda en el SoC para que cualquier top lo reciba ya sincronizado. Los 4.096 ciclos de `por_cnt` eran para las BRAM de la iCE40 | Santiago, 30/10 | `docs/evidencia.md` #4 |
| `debounce_bank` con reset asíncrono, sin `initial` | Mismo motivo: el `initial` se descarta en silencio | Santiago, 30/10 | `docs/evidencia.md` #5 |
| `TICK_BITS` 18 → 17 (muestreo cada ~13,1 ms a 10 MHz) | El ASIC corre a 10 MHz, no a 25 MHz: con 18 bits muestrearía cada 26 ms | Santiago, 30/10 | `docs/evidencia.md` #6 |
| Displays **activo alto** en `asic_top`; la inversión `~seg` queda solo en `game_top` | La polaridad activo bajo es de los displays de la Go Board, no del SoC | Santiago, 26/10 | `docs/evidencia.md` #7 |
| Sincronizador de 2 FF por botón dentro de `debounce_bank` | Los botones son asíncronos al reloj; sin sincronizador hay riesgo de metaestabilidad que el STA no puede ver | Santiago, 30/10 | `docs/evidencia.md` #8 |
| Contador de ciclos extraído a módulo propio (`pochoco_cycle_counter u_cycle_counter`) | Poder identificarlo después de la síntesis y en el layout (3.3 y 3.6) | Lucas, 1/11 | `rtl/pochoco_cycle_counter.v` |

## Memoria y programa (3.2)

| Decisión | Por qué | Quién / cuándo | Detalle |
|---|---|---|---|
| Contrato fijo de `rtl/game_rom.v` (`addr_i` de 8 bits = palabra, `case` combinacional, `default` 0), generado por `sw/assembler.py --rom` | Que las dos estrategias de memoria y la ROM provisoria usen la misma interfaz; 8 bits = 256 palabras, el límite recomendado | Santiago (contrato) y Matias (assembler), 30/10–1/11 | `docs/memoria.md` |
| Estrategia seleccionable con el parámetro `MemStrategy` (`"rom"` / `"ff"`) y el define `POCHOCO_MEM_FF` en un flujo aparte (`flow/asic_top_ff`) | Comparar las dos estrategias con el mismo RTL | Matias, 1/11 | `docs/memoria.md` |
| RAM de datos de 8 palabras en la estrategia ROM (el juego usa 0) | Que el SoC siga siendo de propósito general con un costo acotado | Matias, 1/11 | `docs/memoria.md` |
| **ROM como estrategia de la corrida final** | La de flip-flops ocupa 3,9 veces más área de celdas (die de 1,571 contra 0,441 mm²), congestiona mucho más el ruteo y no cierra por 1 violación de antena | Grupo, 1/11 | `results/memoria.csv`, `docs/signoff.md` |
| Constantes de `game.s` recalculadas para 10 MHz (3 s, 2 s y 1 décima, esta última dos veces) | `CLOCK_PERIOD` = 100 ns | Matias, 1/11 | cabecera de `sw/game.s` |

## Restricciones y configuración de LibreLane

| Decisión | Por qué | Quién / cuándo | Detalle |
|---|---|---|---|
| SDC propio (`flow/asic_top/asic_top.sdc`) basado en el genérico de LibreLane; **`rst_ni` como false path** | El reset es asíncrono y su liberación ya está sincronizada; la red interna de reset sí se analiza (recovery/removal) | Santiago, 30/10 | comentarios de `asic_top.sdc` |
| Entradas y salidas con 20 % del período de retardo de I/O | Conservador: supone que el macro se conecta a lógica sincrónica del mismo reloj | Santiago, 30/10 | `asic_top.sdc` |
| `SYNTH_KEEP_HIERARCHY_MODULES` = register file, ALU, contador | Conservar sus nombres después de la síntesis y en el layout (3.3 y 3.6) | Lucas, 1/11 | `flow/asic_top/config.json` |
| Pines agrupados por función, un lado por grupo (oeste reloj y reset, sur botones y LEDs, norte displays, este SPI); `ERRORS_ON_UNMATCHED_IO = both` | Ruteo ordenado al integrar el macro; el flujo falla si sobra o falta un pin | Santiago, 1/11 | `docs/floorplan.md` |
| Excluir las celdas de retardo `dly*` (`EXTRA_EXCLUDED_CELLS`) | `repair_design` las usaba como buffers de fanout. Son lentas a propósito: eran el 55 % de la ruta crítica. Sin ellas, el setup en ss mejora de 37,6 a 54,2 ns y el área baja 7 % | Santiago, 1/11 | `docs/signoff.md` |
| Habilitar el DRC de KLayout con el runset del PDK | LibreLane lo salta en `gf180mcuD`; así hay dos DRC independientes | Santiago, 1/11 | `docs/signoff.md` |
| **No** usar `DESIGN_REPAIR_MAX_SLEW_PCT = 60` | En dos corridas el repair no terminó; las violaciones de slew se explican en lugar de forzarlas | Santiago, 1/11 | `docs/signoff.md` |

## Timing (3.4)

| Decisión | Por qué | Quién / cuándo | Detalle |
|---|---|---|---|
| Registro `boff_q` en el LSU | Acorta la ruta crítica alineación → write-back: los endpoints que violan en `max_ss` a 60 ns bajan de 191 a 10, con +2 FF | Lucas, 1/11 | `docs/timing.md` |
| Rehacer el barrido de período con la configuración final (sin `dly*`): 100/60/50/40 ns por defecto y 40/35/30 ns con `PL_RESIZER_SETUP_SLACK_MARGIN = 14` | El primer barrido se hizo con las celdas de retardo. Con la configuración final el menor período que cierra es **50 ns** por defecto y **30 ns** con margen (no se probó menos) | Lucas y Santiago, 2/11 | `docs/timing.md`, `results/timing.csv` |
