#!/usr/bin/env python3
"""Clasifica las violaciones de max slew de una corrida por bloque del diseno (3.6).

Uso:
  python3 scripts/slew_por_bloque.py flow/asic_top/runs/<corrida> [corner]

Lee <corrida>/55-openroad-stapostpnr/<corner>/checks.rpt (por defecto
max_ss_125C_4v50) y el netlist final. Cada pin que viola se asigna a la red
que lo excita: red de reset (u_pochoco.rst_ni y los buffers que la reparten),
register file (redes internas de u_rf), ALU, memoria o resto del core.
"""

import collections
import glob
import re
import sys

RE_CELDA = re.compile(r"^\s*(gf180mcu_\w+)\s+(\\\S+|\w+)\s*\((.*?)\);", re.M | re.S)
RE_PIN = re.compile(r"\.(\w+)\(\s*(\\\S+|[^()\s]+)?\s*\)")
RE_VIOL = re.compile(r"^(\S+/\w+)\s+[\d.]+\s+[\d.]+\s+-[\d.]+\s+\(VIOLATED\)", re.M)


def main():
    run = sys.argv[1].rstrip("/")
    corner = sys.argv[2] if len(sys.argv) > 2 else "max_ss_125C_4v50"
    nl = open(f"{run}/final/nl/asic_top.nl.v").read()

    pin_red, cargas = {}, collections.defaultdict(list)
    for tipo, inst, cuerpo in RE_CELDA.findall(nl):
        inst = inst.lstrip("\\")
        for pin, red in RE_PIN.findall(cuerpo):
            if not red:
                continue
            red = red.lstrip("\\")
            pin_red[f"{inst}/{pin}"] = red
            if pin not in ("Z", "ZN", "Q"):
                cargas[red].append((tipo, inst))

    # Arbol de reset: desde rst_ni, siguiendo solo buffers.
    reset, pendientes = set(), ["u_pochoco.rst_ni"]
    while pendientes:
        red = pendientes.pop()
        if red in reset:
            continue
        reset.add(red)
        for tipo, inst in cargas[red]:
            if re.search(r"__(buf|clkbuf)_", tipo) and f"{inst}/Z" in pin_red:
                pendientes.append(pin_red[f"{inst}/Z"])

    (rpt,) = glob.glob(f"{run}/*-openroad-stapostpnr/{corner}/checks.rpt")
    texto = open(rpt).read()
    seccion = texto.split("max slew", 1)[1].split("max capacitance", 1)[0]
    pines = RE_VIOL.findall(seccion)

    bloques = collections.Counter()
    for pin in pines:
        red = pin_red.get(pin.replace("\\", ""), "")
        if red in reset:
            bloques["red de reset"] += 1
        elif "u_rf/" in red:
            bloques["register file (u_rf)"] += 1
        elif "u_alu" in red:
            bloques["ALU"] += 1
        elif "g_mem" in red:
            bloques["memoria"] += 1
        elif "cycle_counter" in red:
            bloques["contador de ciclos"] += 1
        else:
            bloques["resto del core"] += 1

    print(f"{rpt}: {len(pines)} pines con max slew violado "
          f"(arbol de reset: {len(reset)} redes)")
    for bloque, n in bloques.most_common():
        print(f"{n:6d}  {bloque}")


if __name__ == "__main__":
    main()
