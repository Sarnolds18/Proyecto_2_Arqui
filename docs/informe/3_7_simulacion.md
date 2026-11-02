# 3.7 Simulación funcional post-síntesis

El objetivo es mostrar que el netlist que genera LibreLane se comporta igual que el RTL:
mismo programa, mismos estímulos, mismos ciclos. Detalle y comandos en
`docs/simulacion_post_sintesis.md`.

## Programa con los tiempos acortados

A 10 MHz, la espera de 3 s son 30 millones de ciclos por ronda, y simular eso sobre el
netlist toma horas. `scripts/game_sim.py` genera `sim/build/game_sim.s` desde `sw/game.s`
dividiendo por 100 las constantes de tiempo:

| Constante | `game.s` (10 MHz) | `game_sim.s` |
|---|---|---|
| Espera antes del objetivo (3 s) | 30.000.000 ciclos | 300.000 |
| Pausa (2 s) | 20.000.000 | 200.000 |
| Décima de segundo | 1.000.000 | 10.000 |

Las instrucciones y las direcciones no cambian, solo esos inmediatos (recalculados como
`lui` + `addi`). El hardware tampoco cambia: el *debounce* sigue con `TICK_BITS = 17`
(muestrea cada 131.072 ciclos y acepta un cambio después de 2 muestras iguales), así que
el testbench mantiene cada botón apretado 300.000 ciclos. **Las dos simulaciones, RTL y
netlist, usan este mismo programa y esta misma configuración.**

## Testbench

`sim/tb_game_fixed_stimuli.v` instancia `asic_top`, el mismo top que sintetiza
LibreLane, así que el mismo archivo sirve para el RTL y para el netlist. Aprieta los
botones en **ciclos fijos**, sin mirar los LEDs para decidir. Si el netlist tuviera un
ciclo de diferencia en cualquier punto, los eventos quedarían corridos y la comparación
fallaría. El juego es determinista desde el reset (el generador pseudoaleatorio se
siembra con el contador de ciclos), así que el objetivo de la primera ronda es siempre
`0010`.

Escenario:

1. Ciclo 350.000: botón `0001`, con el objetivo `0010` encendido (botón incorrecto).
2. Ciclo 1.000.000: botón `0010`, en la ronda reiniciada (botón correcto).

El testbench registra cada cambio de los LEDs y de los displays con el ciclo en que
ocurre, y al final revisa que haya aparecido `EE`, que la ronda se haya reiniciado y que se
haya medido una ronda correcta.

## Resultado en RTL

Log de `sim/run_fixed_stimuli.sh rtl`:

| Ciclo | LEDs | Display | Qué pasó |
|---|---|---|---|
| 21 | `1111` | `00` | Sale del reset: fase inicial, los 4 LEDs encendidos |
| 300.045 | `0010` | `00` | Termina la espera (300.000 ciclos): se enciende el objetivo |
| 589.848 | `0000` | `EE` | El *debounce* acepta el botón incorrecto: error |
| 639.954 | `1111` | `00` | **La ronda se reinicia** |
| 939.978 | `0010` | `00` | Nueva espera de 300.000 ciclos: objetivo encendido |
| 1.245.563 | `0010` | `30` | El *debounce* acepta el botón correcto: se muestra el tiempo |

La ronda correcta mide **305.585 ciclos**, desde que se enciende el objetivo hasta que se
muestra el resultado. Con una décima de 10.000 ciclos son 30,5 décimas, y el display
muestra `30` (el programa trunca). Ese tiempo incluye los ~245.000 ciclos que tarda el
*debounce* en aceptar la pulsación, que en la FPGA también están (a 10 MHz son ~25 ms).

El testbench además cuenta los accesos de datos a RAM (0) y la dirección de instrucción
más alta pedida (`0x18c`), que respaldan el conteo de palabras de 3.2.

## Resultado en el netlist

El netlist incluye el programa: con la ROM, cada palabra se convierte en compuertas.
Por eso se sintetiza aparte, con la ROM de `game_sim.s`, en `flow/asic_top_sim`. Ese flujo
tiene la **misma configuración de síntesis** que la corrida final (`flow/asic_top`): los
mismos archivos RTL, `SYNTH_KEEP_HIERARCHY_MODULES` con el register file, la ALU y el
contador, y las celdas `dly*` excluidas. Las únicas diferencias son el contenido de la ROM
y los parámetros de pasos posteriores a la síntesis (pines, DRC de KLayout), que no afectan
el netlist.

El netlist (`CP100_U40_sim2/06-yosys-synthesis/asic_top.nl.v`, 5.617 celdas) se simula
con Icarus usando los modelos Verilog de las celdas de GF180 (`gf180mcu_fd_sc_mcu7t5v0`) en
modo funcional, sin retardos. Después, `run_fixed_stimuli.sh compara` revisa los dos logs
línea por línea:

```text
IGUALES: sim/build/rtl_rom.log y sim/build/netlist.log tienen los mismos eventos en los mismos ciclos
```

- **Ronda correcta:** el netlist mide los mismos **305.585 ciclos** y muestra `30`.
- **Pulsación incorrecta:** el netlist muestra `EE` en el ciclo 589.848 y reinicia la ronda
  en el ciclo 639.954, igual que el RTL.

Se hizo dos veces: primero con una síntesis anterior a la optimización del LSU de 3.4
(`CP100_U40_sim`, 67 min de simulación) y después con el RTL final (`CP100_U40_sim2`). Las
dos dieron **IGUALES**.

## Qué demuestra y qué no

- **Demuestra** que la síntesis conserva la función del diseño completo, incluidos la ROM
  generada por el assembler, el *debounce*, el contador de ciclos y el core.
- **Demuestra que el reset funciona en silicio.** En el netlist no hay bloques `initial` ni
  valores iniciales: todos los FF arrancan en `X`. Que el juego funcione igual muestra que
  el reset externo (3.1) lleva todo el estado a un valor conocido. Si quedara algún FF que
  dependiera de un valor inicial (como el `initial` del *debounce* del Proyecto 2), sus `X`
  se propagarían a las salidas y la comparación fallaría.
- **No demuestra** que el diseño cumpla timing: la simulación es sin retardos. Eso lo
  garantiza el análisis estático de 3.4 y 3.6 (setup y hold con WS ≥ 0 y TNS = 0 en todos
  los corners). La simulación post-PnR con SDF, que es opcional, no se hizo.
- Los tiempos acortados no cambian el control del programa: solo cambian inmediatos, y las
  dos simulaciones usan el mismo programa.

## Cómo correrlo

```bash
sim/run_fixed_stimuli.sh rtl                 # RTL, ~1,5 min -> sim/build/rtl_rom.log
scripts/run_sweep.sh -d flow/asic_top_sim -s sim2 -p "100" -u "40" -- --to Yosys.Synthesis
sim/run_fixed_stimuli.sh netlist flow/asic_top_sim/runs/CP100_U40_sim2/06-yosys-synthesis/asic_top.nl.v
sim/run_fixed_stimuli.sh compara sim/build/rtl_rom.log sim/build/netlist.log
```
