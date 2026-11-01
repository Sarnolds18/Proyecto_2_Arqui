#!/usr/bin/env python3
"""Genera la variante de simulacion de game.s con los tiempos acortados (3.7).

Uso:
  python3 -B scripts/game_sim.py sw/game.s <salida.s> [divisor]

Busca cada constante de tiempo de game.s, escrita como
    lui  rd, HI
    addi rd, rd, LO   # ... ciclos ...
y la reemplaza por (HI << 12) + LO dividido por el divisor (100 por defecto),
otra vez como lui + addi. Asi el programa simulado tiene exactamente las
mismas instrucciones en las mismas direcciones y solo cambian esos
inmediatos: 3 s, 2 s y la decima pasan a durar 1/100 (300.000, 200.000 y
10.000 ciclos a 10 MHz). El debounce no se toca (es hardware: el netlist
tiene TICK_BITS = 17 fijo), por eso el divisor no puede ser mucho mayor: con
100, el tiempo de reaccion simulado (dominado por el debounce, ~130k-260k
ciclos) sigue cabiendo en 0-99 decimas.

La simulacion RTL y la post-sintesis usan el mismo programa generado.
"""

import re
import sys
from pathlib import Path

LUI = re.compile(r"^(\s*)lui\s+(\w+)\s*,\s*(\S+)\s*(#.*)?$")
ADDI = re.compile(r"^(\s*)addi\s+(\w+)\s*,\s*(\w+)\s*,\s*(\S+)\s*(#.*)?$")


def split_hi_lo(value):
    """lui/addi para value: addi suma 12 bits con signo, asi que si el bit 11
    esta en 1 se sube hi en 1 y lo queda negativo."""
    lo = value & 0xFFF
    if lo >= 0x800:
        lo -= 0x1000
    return (value - lo) >> 12, lo


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    source, dest = sys.argv[1], sys.argv[2]
    divisor = int(sys.argv[3]) if len(sys.argv) == 4 else 100

    lines = Path(source).read_text().splitlines()
    out = [f"# GENERADO por scripts/game_sim.py desde {source}: constantes de tiempo / {divisor}.",
           "# No editar; regenerar. Solo para simulacion (sim/run_fixed_stimuli.sh).",
           ""]
    changed = 0
    i = 0
    while i < len(lines):
        lui = LUI.match(lines[i])
        addi = ADDI.match(lines[i + 1]) if lui and i + 1 < len(lines) else None
        if (lui and addi and addi.group(5) and "ciclos" in addi.group(5)
                and lui.group(2) == addi.group(2) == addi.group(3)):
            value = (int(lui.group(3), 0) << 12) + int(addi.group(4), 0)
            if value % divisor:
                sys.exit(f"{source}:{i + 2}: {value} no es divisible por {divisor}")
            hi, lo = split_hi_lo(value // divisor)
            rd = lui.group(2)
            out.append(f"{lui.group(1)}lui  {rd}, {hi:#x}")
            out.append(f"{addi.group(1)}addi {rd}, {rd}, {lo:<6} "
                       f"# [SIM] {value // divisor:,} ciclos = {value:,} / {divisor}")
            changed += 1
            i += 2
            continue
        out.append(lines[i])
        i += 1

    Path(dest).write_text("\n".join(out) + "\n")
    print(f"{changed} constantes de tiempo / {divisor} -> {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()
