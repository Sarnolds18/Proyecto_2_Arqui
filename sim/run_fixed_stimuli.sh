#!/usr/bin/env bash
# Simulacion de la seccion 3.7: sim/tb_game_fixed_stimuli.v sobre el RTL o
# sobre el netlist post-sintesis de LibreLane, con el mismo programa
# (game.s con los tiempos / 100, ver scripts/game_sim.py).
#
# Uso (desde la raiz del repo):
#   sim/run_fixed_stimuli.sh rtl [rom|ff]          RTL con la estrategia de memoria dada (rom por defecto)
#   sim/run_fixed_stimuli.sh netlist <netlist.v>   netlist sin retardos, p. ej.
#       flow/asic_top/runs/<tag>/06-yosys-synthesis/asic_top.nl.v
#   sim/run_fixed_stimuli.sh compara <log1> <log2>  compara dos logs (sin la linea de $finish ni la de RTL)
#
# Los logs quedan en sim/build/<modo>.log. Para el netlist se usan los modelos
# Verilog de las celdas de GF180 ($PDK_ROOT/gf180mcuD, como los baja LibreLane
# en ~/.ciel) en modo funcional, sin retardos.
#
# OJO: el netlist tiene el programa adentro (la ROM o los valores de reset
# son celdas), asi que para comparar con el RTL hay que sintetizar con la
# ROM generada desde sim/build/game_sim.s, no la de sw/game.s. Ver
# docs/simulacion_post_sintesis.md.

set -eu
cd "$(dirname "${BASH_SOURCE[0]}")/.."

BUILD=sim/build
mkdir -p "$BUILD"

programa() {
  python3 -B scripts/game_sim.py sw/game.s "$BUILD/game_sim.s"
  python3 -B sw/assembler.py "$BUILD/game_sim.s" "$BUILD/game_sim.hex" --rom "$BUILD/game_rom.v"
}

filtra() {
  grep -v -e '\$finish called' -e '^RTL: ' -e '^VCD info' "$1"
}

modo="${1:-}"
case "$modo" in
  rtl)
    estrategia="${2:-rom}"
    defs=()
    [ "$estrategia" = ff ] && defs=(-DPOCHOCO_MEM_FF)
    programa
    rtl=$(ls rtl/*.v rtl/espino_core/*.v | grep -v -e '/game_rom.v$' -e '/game_top.v$')
    iverilog -g2012 "${defs[@]}" -o "$BUILD/tb_rtl_$estrategia.vvp" \
      sim/tb_game_fixed_stimuli.v $rtl "$BUILD/game_rom.v"
    vvp -n "$BUILD/tb_rtl_$estrategia.vvp" | tee "$BUILD/rtl_$estrategia.log"
    ;;
  netlist)
    netlist="${2:?falta el netlist}"
    pdk_root="${PDK_ROOT:-$HOME/.ciel}"
    celdas="$pdk_root/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog"
    [ -f "$celdas/gf180mcu_fd_sc_mcu7t5v0.v" ] || {
      echo "error: no estan los modelos de celdas en $celdas" >&2; exit 1; }
    modelos=("$celdas/gf180mcu_fd_sc_mcu7t5v0.v")
    [ -f "$celdas/primitives.v" ] && modelos=("$celdas/primitives.v" "${modelos[@]}")
    iverilog -g2012 -DGATE_LEVEL -DFUNCTIONAL -DUNIT_DELAY=#0 -o "$BUILD/tb_netlist.vvp" \
      -I "$celdas" sim/tb_game_fixed_stimuli.v "$netlist" "${modelos[@]}"
    vvp -n "$BUILD/tb_netlist.vvp" | tee "$BUILD/netlist.log"
    ;;
  compara)
    a="${2:?falta log 1}" b="${3:?falta log 2}"
    if diff <(filtra "$a") <(filtra "$b"); then
      echo "IGUALES: $a y $b tienen los mismos eventos en los mismos ciclos"
    else
      echo "DISTINTOS: ver diff arriba"; exit 1
    fi
    ;;
  *)
    sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
