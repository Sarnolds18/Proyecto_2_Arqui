#!/usr/bin/env python3
"""Barrido de utilizacion (seccion 3.5): CSV con area, costo y congestion, y grafico.

Uso:
  python3 scripts/floorplan.py -o results/floorplan.csv -g results/floorplan.png \
      flow/asic_top/runs/CP100_U*_pines

Ademas de las columnas de extract_metrics.py agrega:
  - grt_uso_pct, grt_overflow: uso de recursos de ruteo y overflow total del
    ruteo global (tabla "Total" de GRT en el log de OpenROAD.GlobalRouting).
  - drt_viol_iter0: violaciones que deja la primera iteracion del ruteo
    detallado (route__drc_errors__iter:0). Mide cuanto le cuesta al ruteador
    meter los cables en el area disponible.
  - die_mm2, costo_usd: area del die y costo a US$23.000/mm2 (escalado lineal).
"""

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_metrics as em  # noqa: E402

USD_POR_MM2 = 23000
COLUMNAS = em.COLUMNAS + ["grt_uso_pct", "grt_overflow", "drt_viol_iter0",
                          "die_mm2", "costo_usd"]
# "Total   217554   50497   23.21%   0 /  0 /  0"
RE_GRT = re.compile(r"^Total\s+\d+\s+\d+\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", re.M)


def congestion_grt(run):
    logs = sorted(run.glob("*-openroad-globalrouting/openroad-globalrouting.log"))
    if not logs:
        return None, None
    m = RE_GRT.findall(logs[-1].read_text(errors="replace"))
    if not m:
        return None, None
    uso, _, _, overflow = m[-1]
    return float(uso), int(overflow)


def fila(run):
    r = em.fila(run)
    m = em.cargar_json(run / "final" / "metrics.json") or {}
    r["grt_uso_pct"], r["grt_overflow"] = congestion_grt(run)
    r["drt_viol_iter0"] = m.get("route__drc_errors__iter:0")
    if r.get("area_die_um2") is not None:
        r["die_mm2"] = round(r["area_die_um2"] / 1e6, 4)
        r["costo_usd"] = round(r["area_die_um2"] / 1e6 * USD_POR_MM2)
    return r


def grafico(filas, salida):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    filas = [r for r in filas if r.get("fp_core_util") is not None]
    filas.sort(key=lambda r: r["fp_core_util"])
    x = [r["fp_core_util"] for r in filas]
    paneles = [
        ("drt_viol_iter0", "Violaciones tras la 1a iteración\ndel ruteo detallado"),
        ("grt_uso_pct", "Uso de recursos del\nruteo global (%)"),
        ("die_mm2", "Área del die (mm²)"),
    ]
    azul, tinta, tinta2, grilla = "#2a78d6", "#0b0b0b", "#52514e", "#e4e3df"

    fig, axs = plt.subplots(len(paneles), 1, figsize=(6.5, 7.5), sharex=True)
    for ax, (clave, titulo) in zip(axs, paneles):
        pts = [(xi, r[clave]) for xi, r in zip(x, filas) if r.get(clave) is not None]
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=azul, lw=2, zorder=2)
            for (xi, yi), r in zip(pts, [r for r in filas if r.get(clave) is not None]):
                cierra = r.get("cierra") == "si"
                ax.scatter([xi], [yi], s=64, zorder=3, marker="o" if cierra else "X",
                           facecolor=azul if cierra else "white", edgecolor=azul, lw=2)
                ax.annotate(f"{yi:g}", (xi, yi), textcoords="offset points",
                            xytext=(0, 8), ha="center", fontsize=8, color=tinta2)
        # Corridas que no llegaron al final (p. ej. placement imposible): sin
        # metricas, se marcan con una linea vertical.
        for r in filas:
            if r.get("estado") != "completa":
                ax.axvline(r["fp_core_util"], color=tinta2, ls="--", lw=1, zorder=1)
        ax.set_ylabel(titulo, fontsize=9, color=tinta)
        ax.grid(True, color=grilla, lw=0.8)
        ax.set_axisbelow(True)
        ax.margins(y=0.25)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(colors=tinta2, labelsize=8)
    axs[-1].set_xlabel("FP_CORE_UTIL (%)", fontsize=9, color=tinta)
    axs[-1].set_xticks(x)
    fig.suptitle("Barrido de utilización — asic_top, T = 100 ns\n"
                 "● cierra   ✕ no cierra   - - - el flujo no termina",
                 fontsize=10, color=tinta)
    fig.tight_layout()
    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, dpi=200)
    print(f"grafico -> {salida}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corridas", nargs="+", type=Path, help="carpetas de corrida")
    ap.add_argument("-o", "--salida", type=Path, help="CSV de salida (por defecto stdout)")
    ap.add_argument("-g", "--grafico", type=Path, help="PNG del grafico")
    args = ap.parse_args()

    filas = [fila(run) for run in sorted(args.corridas) if run.is_dir()]
    if not filas:
        sys.exit("error: ninguna carpeta de corrida valida")

    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
    f = open(args.salida, "w", newline="") if args.salida else sys.stdout
    w = csv.DictWriter(f, fieldnames=COLUMNAS)
    w.writeheader()
    for r in filas:
        w.writerow({k: ("" if r.get(k) is None else r[k]) for k in COLUMNAS})
    if args.salida:
        f.close()
        print(f"{len(filas)} corrida(s) -> {args.salida}", file=sys.stderr)

    cerradas = [r for r in filas if r.get("cierra") == "si" and r.get("die_mm2")]
    if cerradas:
        menor = min(cerradas, key=lambda r: r["die_mm2"])
        print(f"area minima que cierra: {menor['corrida']} -> {menor['die_mm2']} mm2 "
              f"= US${menor['costo_usd']:,}", file=sys.stderr)
    if args.grafico:
        grafico(filas, args.grafico)


if __name__ == "__main__":
    main()
