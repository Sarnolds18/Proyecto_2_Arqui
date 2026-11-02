# 3.7 Simulación funcional post-síntesis

## Programa con los tiempos acortados

Simular 3 s a 10 MHz son 30 millones de ciclos por ronda; en el netlist eso tarda horas.
`scripts/game_sim.py` genera `sim/build/game_sim.s` desde `sw/game.s` dividiendo por 100
las cuatro constantes de tiempo (3 s → 300.000 ciclos, 2 s → 200.000, 1 décima → 10.000).
Las instrucciones y direcciones son las mismas; solo cambian esos inmediatos. El
hardware no cambia: el debounce sigue con `TICK_BITS = 17`, por eso cada pulsación del
testbench dura 300.000 ciclos. **Las dos simulaciones usan este mismo programa.**

## Testbench

`sim/tb_game_fixed_stimuli.v` instancia `asic_top` (el mismo top que el netlist) y
aprieta botones en ciclos fijos (no mira los LEDs para decidir). Registra cada cambio de
los LEDs y los displays con su ciclo:

1. Ciclo 350.000: botón `0001` con el objetivo `0010` → display `EE` y la ronda se
   reinicia (LEDs `1111` de nuevo).
2. Ciclo 1.000.000: botón `0010` (correcto) → el display muestra el tiempo en décimas.

Resultado RTL: objetivo encendido en el ciclo 939.978, resultado en el ciclo 1.245.563
(**305.585 ciclos**), display `30` décimas (305.585 / 10.000 = 30,5).

## Cómo correrlo

```bash
sim/run_fixed_stimuli.sh rtl                 # RTL -> sim/build/rtl_rom.log (~1,5 min)

# Netlist: el programa está dentro del netlist, así que se sintetiza con la ROM de
# game_sim.s (flow/asic_top_sim usa sim/build/game_rom.v, que genera el paso anterior).
scripts/run_sweep.sh -d flow/asic_top_sim -s sim2 -p "100" -u "40" -- --to Yosys.Synthesis
sim/run_fixed_stimuli.sh netlist flow/asic_top_sim/runs/CP100_U40_sim2/06-yosys-synthesis/asic_top.nl.v

sim/run_fixed_stimuli.sh compara sim/build/rtl_rom.log sim/build/netlist.log
```

El netlist se simula sin retardos con los modelos Verilog de las celdas de GF180. El
script los busca en `~/.ciel/ciel/gf180mcu/versions/<revisión>/gf180mcuD/...`, que es
donde los deja LibreLane, o bajo `$PDK_ROOT`. `flow/asic_top_sim` tiene la misma
configuración de síntesis que `flow/asic_top` (RTL, módulos con jerarquía conservada y
celdas `dly*` excluidas); solo cambia el contenido de la ROM.

## Resultado

**RTL final.** Corrida `flow/asic_top_sim/runs/CP100_U40_sim2` (solo síntesis, con el
RTL final: memoria ROM, contador como módulo, `boff_q` en el LSU y la misma configuración
de síntesis que `CP100_U40_final`). Su netlist (5.617 celdas, 163.591 µm², con la ROM de
`game_sim.s`) simulado con Icarus contra el log RTL: `compara` da **IGUALES**. El netlist
reproduce evento por evento el log RTL: el botón incorrecto muestra `EE` y reinicia la
ronda, y la ronda correcta mide **305.585 ciclos** (display `30`), igual que el RTL.

**Antes.** La corrida `flow/asic_top_sim/runs/CP100_U40_sim` (síntesis anterior a la
optimización del LSU de 3.4 y a los cambios de configuración de la corrida final) también
dio **IGUALES** (67 min de simulación). La simulación RTL da exactamente los mismos
eventos con el RTL de las dos síntesis, así que el cambio de `boff_q` no alteró el
comportamiento del juego.
