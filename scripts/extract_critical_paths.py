#!/usr/bin/env python3
"""Guarda las peores rutas de timing de una corrida en <corrida>/rutas_criticas.rpt.

Uso:
  python3 scripts/extract_critical_paths.py [-n 5] <corrida> [<corrida> ...]

Lee <corrida>/*-openroad-stapostpnr/<corner>/max.rpt (setup) y min.rpt (hold)
en los corners del informe (tipico nom_tt_025C_5v00 y mas lento
max_ss_125C_4v50) y copia las N primeras rutas de cada uno, tal como las
escribe OpenSTA (ya vienen ordenadas de peor a mejor slack). Los max/min.rpt
completos pesan decenas de MB por corrida y no se versionan; este archivo si.
"""

import argparse
import sys
from pathlib import Path

CORNERS = ("nom_tt_025C_5v00", "max_ss_125C_4v50")
REPORTES = (("max.rpt", "setup"), ("min.rpt", "hold"))


def peores_rutas(rpt, n):
    """Devuelve las n primeras rutas: cada una desde 'Startpoint:' hasta la
    linea del slack, inclusive."""
    rutas, actual = [], None
    with open(rpt) as f:
        for linea in f:
            if linea.startswith("Startpoint:"):
                actual = [linea]
            elif actual is not None:
                actual.append(linea)
                if "slack (" in linea:
                    rutas.append("".join(actual))
                    actual = None
                    if len(rutas) == n:
                        break
    return rutas


def procesar(run, n):
    sta = sorted(run.glob("*-openroad-stapostpnr"))
    if not sta:
        print(f"{run.name}: sin STA post-PnR, se salta", file=sys.stderr)
        return False
    sta = sta[-1]
    salida = [f"# Peores {n} rutas por corner y chequeo, extraidas de {sta.name}/<corner>/max.rpt y min.rpt",
              f"# Corrida: {run.name}", ""]
    for corner in CORNERS:
        for archivo, tipo in REPORTES:
            rpt = sta / corner / archivo
            titulo = f"{tipo} - {corner} ({sta.name}/{corner}/{archivo})"
            salida += ["=" * 78, titulo, "=" * 78, ""]
            if not rpt.exists():
                salida += ["(reporte no encontrado)", ""]
                continue
            rutas = peores_rutas(rpt, n)
            for i, ruta in enumerate(rutas, 1):
                salida += [f"--- ruta {i} de {len(rutas)} ---", ruta]
    destino = run / "rutas_criticas.rpt"
    destino.write_text("\n".join(salida))
    print(f"{run.name}: -> {destino}", file=sys.stderr)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corridas", nargs="+", type=Path)
    ap.add_argument("-n", type=int, default=5, help="rutas por corner y chequeo (5)")
    args = ap.parse_args()
    ok = [procesar(r, args.n) for r in args.corridas if r.is_dir()]
    if not any(ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
