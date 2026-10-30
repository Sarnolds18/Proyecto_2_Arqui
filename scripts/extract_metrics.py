#!/usr/bin/env python3
"""Extrae las metricas de corridas de LibreLane a un CSV (una fila por corrida).

Uso:
  python3 scripts/extract_metrics.py -o results/timing.csv flow/asic_top/runs/CP*_rom
  python3 scripts/extract_metrics.py flow/asic_top/runs/*      # CSV a stdout

Lee <corrida>/final/metrics.json y <corrida>/resolved.json. Las columnas
vacias son metricas que la corrida no alcanzo a generar (p. ej. una corrida
cortada con --to). Los corners del informe son el tipico (nom_tt_025C_5v00)
y el mas lento (max_ss_125C_4v50); "peor" es el peor de los 9 corners.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

TIPICO = "nom_tt_025C_5v00"
LENTO = "max_ss_125C_4v50"
CORNERS_INFORME = (TIPICO, LENTO)

COLUMNAS = [
    "corrida", "estado", "cierra", "clock_period_ns", "fp_core_util",
    "setup_ws_tt", "setup_tns_tt", "hold_ws_tt", "hold_tns_tt",
    "setup_ws_ss", "setup_tns_ss", "hold_ws_ss", "hold_tns_ss",
    "setup_ws_peor", "setup_tns_peor", "hold_ws_peor", "hold_tns_peor",
    "setup_r2r_ws_tt", "setup_r2r_ws_ss", "fmax_r2r_mhz",
    "area_stdcell_um2", "area_core_um2", "area_die_um2", "utilizacion",
    "celdas_stdcell", "flip_flops",
    "drc_magic", "lvs_errores", "antena_redes", "antena_pines",
    "max_cap_viol", "max_slew_viol", "max_fanout_viol",
]


def cargar_json(ruta):
    try:
        with open(ruta) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def corner(m, clave, c):
    return m.get(f"{clave}__corner:{c}")


def cierra(m):
    """Criterio del enunciado: DRC, LVS y antena limpios; setup y hold con
    WS >= 0 y TNS = 0 en los corners del informe. None si faltan metricas."""
    claves = [m.get("magic__drc_error__count"), m.get("design__lvs_error__count"),
              m.get("antenna__violating__nets")]
    for c in CORNERS_INFORME:
        for tipo in ("setup", "hold"):
            claves += [corner(m, f"timing__{tipo}__ws", c),
                       corner(m, f"timing__{tipo}__tns", c)]
    if any(v is None for v in claves):
        return None
    drc, lvs, ant = claves[:3]
    if drc != 0 or lvs != 0 or ant != 0:
        return False
    timing = claves[3:]
    return all(timing[i] >= 0 and timing[i + 1] == 0 for i in range(0, len(timing), 2))


def fila(run):
    m = cargar_json(run / "final" / "metrics.json")
    cfg = cargar_json(run / "resolved.json") or {}
    r = {"corrida": run.name,
         "clock_period_ns": cfg.get("CLOCK_PERIOD"),
         "fp_core_util": cfg.get("FP_CORE_UTIL")}
    if m is None:
        r["estado"] = "sin_metricas"
        return r
    # "Flow complete." tambien aparece con --to; LVS es de las ultimas etapas
    r["estado"] = "completa" if "design__lvs_error__count" in m else "parcial"
    ok = cierra(m)
    r["cierra"] = "" if ok is None else ("si" if ok else "no")

    for suf, c in (("tt", TIPICO), ("ss", LENTO)):
        for tipo in ("setup", "hold"):
            r[f"{tipo}_ws_{suf}"] = corner(m, f"timing__{tipo}__ws", c)
            r[f"{tipo}_tns_{suf}"] = corner(m, f"timing__{tipo}__tns", c)
    for tipo in ("setup", "hold"):
        r[f"{tipo}_ws_peor"] = m.get(f"timing__{tipo}__ws")
        r[f"{tipo}_tns_peor"] = m.get(f"timing__{tipo}__tns")
    r["setup_r2r_ws_tt"] = corner(m, "timing__setup_r2r__ws", TIPICO)
    r["setup_r2r_ws_ss"] = corner(m, "timing__setup_r2r__ws", LENTO)

    # Frecuencia maxima estimada con los caminos registro->registro: su retardo
    # no depende de T, asi que el periodo minimo es T - WS. Los caminos de I/O
    # no sirven para esto porque su retardo de entrada/salida (IO_DELAY_CONSTRAINT)
    # es un porcentaje de T y se achica junto con el. El valor real sale del
    # barrido; esto es solo una estimacion desde una corrida.
    ws = [r["setup_r2r_ws_tt"], r["setup_r2r_ws_ss"]]
    T = r["clock_period_ns"]
    if T is not None and None not in ws and T - min(ws) > 0:
        r["fmax_r2r_mhz"] = round(1000.0 / (T - min(ws)), 3)

    r.update({
        "area_stdcell_um2": m.get("design__instance__area__stdcell"),
        "area_core_um2": m.get("design__core__area"),
        "area_die_um2": m.get("design__die__area"),
        "utilizacion": m.get("design__instance__utilization"),
        "celdas_stdcell": m.get("design__instance__count__stdcell"),
        "flip_flops": m.get("design__instance__count__class:sequential_cell"),
        "drc_magic": m.get("magic__drc_error__count"),
        "lvs_errores": m.get("design__lvs_error__count"),
        "antena_redes": m.get("antenna__violating__nets"),
        "antena_pines": m.get("antenna__violating__pins"),
        "max_cap_viol": m.get("design__max_cap_violation__count"),
        "max_slew_viol": m.get("design__max_slew_violation__count"),
        "max_fanout_viol": m.get("design__max_fanout_violation__count"),
    })
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corridas", nargs="+", type=Path, help="carpetas de corrida")
    ap.add_argument("-o", "--salida", type=Path, help="CSV de salida (por defecto stdout)")
    args = ap.parse_args()

    filas = [fila(run) for run in sorted(args.corridas) if run.is_dir()]
    if not filas:
        sys.exit("error: ninguna carpeta de corrida valida")

    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        f = open(args.salida, "w", newline="")
    else:
        f = sys.stdout
    w = csv.DictWriter(f, fieldnames=COLUMNAS)
    w.writeheader()
    for r in filas:
        w.writerow({k: ("" if r.get(k) is None else r[k]) for k in COLUMNAS})
    if args.salida:
        f.close()
        print(f"{len(filas)} corrida(s) -> {args.salida}", file=sys.stderr)


if __name__ == "__main__":
    main()
