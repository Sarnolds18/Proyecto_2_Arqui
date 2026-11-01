#!/usr/bin/env python3
"""Marca sobre el layout las violaciones de antena que encontro el chequeo previo al
repair (seccion 3.6).

Uso (despues de scripts/capturas.py, que genera el render layout.png):
  python3 scripts/antenas_layout.py flow/asic_top/runs/<corrida> \
      --fondo docs/img/layout.png -o docs/img/antenas.png

Lee <corrida>/*-openroad-checkantennas/reports/antenna_summary.rpt (el primer
chequeo, antes de repair_antennas) y ubica la celda de cada pin afectado en el DEF
final. Imprime la tabla red / pin / capa / razon / posicion.
"""

import argparse
import glob
import re
from pathlib import Path

RE_FILA = re.compile(r"│\s*([\d.]+)\s*│\s*([\d.]+)\s*│\s*([\d.]+)\s*│\s*(\S+)\s*│\s*(\S+)\s*│\s*(\S+)\s*│")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corrida", type=Path)
    ap.add_argument("--fondo", type=Path, help="render del GDS que cubre el die (layout.png)")
    ap.add_argument("-o", "--salida", type=Path, default=Path("docs/img/antenas.png"))
    args = ap.parse_args()

    (rpt,) = sorted(glob.glob(str(args.corrida / "*-openroad-checkantennas/reports/antenna_summary.rpt")))
    filas = [m.groups() for m in RE_FILA.finditer(open(rpt).read())]

    (defp,) = glob.glob(str(args.corrida / "final/def/*.def"))
    deftxt = open(defp).read()
    dbu = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", deftxt).group(1))
    die = [int(v) / dbu for v in re.search(
        r"DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)", deftxt).groups()]

    puntos = []
    print(f"{rpt}: {len(filas)} violaciones")
    for pr, parcial, req, red, pin, capa in filas:
        celda = pin.rsplit("/", 1)[0]
        m = re.search(rf"^\s*- {re.escape(celda)} \S+ .*?PLACED \( (-?\d+) (-?\d+) \)", deftxt, re.M)
        x, y = (int(m.group(1)) / dbu, int(m.group(2)) / dbu) if m else (None, None)
        puntos.append((x, y, red, capa, float(pr)))
        print(f"  {red:32s} {pin:36s} {capa:7s} {parcial}/{req} (P/R {pr})  ({x}, {y}) um")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 8 * (die[3] - die[1]) / (die[2] - die[0]) + 0.6))
    if args.fondo:
        ax.imshow(plt.imread(args.fondo), extent=(die[0], die[2], die[1], die[3]))
    for i, (x, y, red, capa, pr) in enumerate(puntos, 1):
        if x is None:
            continue
        ax.plot(x, y, "o", ms=26, mfc="none", mec="#e3001b", mew=2.5)
        ax.annotate(f"{i}. {red}\n{capa}, P/R {pr:.2f}", (x, y), xytext=(18, 18),
                    textcoords="offset points", fontsize=9, weight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#e3001b", lw=1.5),
                    arrowprops=dict(arrowstyle="-", color="#e3001b", lw=1.5))
    ax.set_xlim(die[0], die[2])
    ax.set_ylim(die[1], die[3])
    ax.set_aspect("equal")
    ax.set_xlabel("x (µm)", fontsize=9)
    ax.set_ylabel("y (µm)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(f"{args.corrida.name}: violaciones de antena antes del repair "
                 f"(corregidas con jumpers y 1 diodo)", fontsize=10)
    fig.tight_layout()
    fig.savefig(args.salida, dpi=100)
    print(f"-> {args.salida}")


if __name__ == "__main__":
    main()
