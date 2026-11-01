#!/usr/bin/env python3
"""Analisis jerarquico de la sintesis de una corrida de LibreLane (seccion 3.3).

Lee <corrida>/06-yosys-synthesis/reports/stat.rpt (estadisticas de Yosys con
los modulos de SYNTH_KEEP_HIERARCHY_MODULES separados) y genera un resumen en
Markdown:
  - area, celdas y flip-flops por modulo, y su fraccion del total;
  - las 5 celdas mas usadas del diseno completo, desglosadas por modulo;
  - la fraccion del area que es el contador de ciclos.
Si el DEF final esta en disco (no se versiona), agrega cuantas celdas de cada
instancia quedaron en el layout despues de place & route.

Uso:
  python3 scripts/analisis_sintesis.py flow/asic_top/runs/<corrida> [-o results/sintesis.md]
"""

import argparse
import glob
import os
import re
import sys
from collections import OrderedDict

# Modulo -> instancia (las rutas son las del netlist de sintesis).
INSTANCIAS = OrderedDict([
    ("espino_register_file", "u_pochoco.u_core.u_rf"),
    ("espino_alu", "u_pochoco.u_core.u_id.u_alu"),
    ("pochoco_cycle_counter", "u_pochoco.u_periph.u_cycle_counter"),
])
CONTADOR = "pochoco_cycle_counter"

RE_SECCION = re.compile(r"^=== (.+) ===$")
RE_CELDA = re.compile(r"^\s+(\d+)\s+\S+\s+(\S+__\S+)$")
RE_AREA = re.compile(r"Chip area for (?:top )?module '\\(\S+)': ([\d.]+)")
RE_SEQ = re.compile(r"of which used for sequential elements: ([\d.]+)")


def leer_stat(path):
    """Devuelve {modulo: {"celdas": {celda: n}, "area": a, "area_seq": s}}
    con las cuentas LOCALES de cada modulo (sin submodulos)."""
    modulos = OrderedDict()
    actual = None
    with open(path) as f:
        for linea in f:
            linea = linea.rstrip("\n")
            m = RE_SECCION.match(linea.strip())
            if m:
                nombre = m.group(1)
                actual = None if nombre == "design hierarchy" else nombre
                if actual:
                    modulos[actual] = {"celdas": OrderedDict(), "area": None,
                                       "area_seq": None}
                continue
            if actual is None:
                continue
            m = RE_CELDA.match(linea)
            if m:
                modulos[actual]["celdas"][m.group(2)] = int(m.group(1))
                continue
            m = RE_AREA.search(linea)
            if m:
                modulos[actual]["area"] = float(m.group(2))
                continue
            m = RE_SEQ.search(linea)
            if m:
                modulos[actual]["area_seq"] = float(m.group(1))
    return modulos


def corto(celda):
    return celda.split("__", 1)[1]


def es_ff(celda):
    return corto(celda).startswith(("dff", "sdff", "latq", "icg"))


def celdas_def(run):
    """Celdas por prefijo de instancia en el DEF final, o None si no esta."""
    defs = glob.glob(os.path.join(run, "final", "def", "*.def"))
    if not defs:
        return None
    total = 0
    por_inst = OrderedDict((m, 0) for m in INSTANCIAS)
    dentro = False
    with open(defs[0]) as f:
        for linea in f:
            if linea.startswith("COMPONENTS"):
                dentro = True
                continue
            if linea.startswith("END COMPONENTS"):
                break
            if dentro and linea.lstrip().startswith("- "):
                nombre = linea.split()[1]
                total += 1
                for mod, inst in INSTANCIAS.items():
                    if nombre.startswith(inst + "/"):
                        por_inst[mod] += 1
    return total, por_inst


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("corrida", help="carpeta de la corrida (runs/<tag>)")
    ap.add_argument("-o", "--salida", help="archivo Markdown de salida (por defecto, stdout)")
    args = ap.parse_args()

    run = args.corrida.rstrip("/")
    stat = os.path.join(run, "06-yosys-synthesis", "reports", "stat.rpt")
    if not os.path.isfile(stat):
        sys.exit(f"error: no existe {stat}")
    modulos = leer_stat(stat)
    if not modulos:
        sys.exit(f"error: {stat} no tiene secciones de modulos")

    top = next(m for m in modulos if m not in INSTANCIAS)
    faltan = [m for m in INSTANCIAS if m not in modulos]
    area_total = sum(d["area"] for d in modulos.values())

    out = []
    w = out.append
    w(f"# Analisis de sintesis: `{os.path.basename(run)}`\n")
    w(f"Fuente: `{os.path.relpath(stat)}` (generado por `scripts/analisis_sintesis.py`).\n")
    if faltan:
        w(f"**Aviso:** estos modulos no aparecen separados en la sintesis (se aplanaron): "
          f"{', '.join(faltan)}. Revisar `SYNTH_KEEP_HIERARCHY_MODULES`.\n")

    # Area por modulo
    w("## Area por modulo\n")
    w("Areas de celdas de la sintesis (antes de place & route: sin buffers de "
      "repair, CTS, tap ni relleno). Para el top, el area es **local** (sin los "
      "submodulos), es decir, todo lo que se aplano en el top.\n")
    w("| Modulo | Instancia | Area (um2) | % del total | Celdas | Flip-flops | % secuencial |")
    w("|---|---|---:|---:|---:|---:|---:|")
    filas = []
    for mod, d in modulos.items():
        inst = INSTANCIAS.get(mod, "(top, resto del SoC)")
        celdas = sum(d["celdas"].values())
        ffs = sum(n for c, n in d["celdas"].items() if es_ff(c))
        filas.append((mod, inst, d["area"], celdas, ffs, d["area_seq"]))
    for mod, inst, area, celdas, ffs, seq in sorted(filas, key=lambda x: -x[2]):
        w(f"| `{mod}` | `{inst}` | {area:,.0f} | {pct(area, area_total):.1f} % | "
          f"{celdas:,} | {ffs:,} | {pct(seq or 0, area):.1f} % |")
    celdas_tot = sum(f[3] for f in filas)
    ffs_tot = sum(f[4] for f in filas)
    w(f"| **Total** | | **{area_total:,.0f}** | 100 % | **{celdas_tot:,}** | **{ffs_tot:,}** | |\n")

    mayor = max((f for f in filas if f[0] in INSTANCIAS), key=lambda x: x[2], default=None)
    if mayor:
        w(f"Modulo con mas area (de los que se conservan): **`{mayor[0]}`**, "
          f"{mayor[2]:,.0f} um2 ({pct(mayor[2], area_total):.1f} %).\n")
    if CONTADOR in modulos:
        a = modulos[CONTADOR]["area"]
        w(f"Contador de ciclos (`{CONTADOR}`): **{a:,.0f} um2 = "
          f"{pct(a, area_total):.2f} % del area de celdas**.\n")

    # Top-5 celdas
    totales = OrderedDict()
    for d in modulos.values():
        for c, n in d["celdas"].items():
            totales[c] = totales.get(c, 0) + n
    top5 = sorted(totales.items(), key=lambda x: -x[1])[:5]
    cols = [top] + [m for m in INSTANCIAS if m in modulos]
    w("## Las 5 celdas mas usadas\n")
    w("Cantidad total en el diseno y cuantas hay en cada modulo.\n")
    w("| Celda | Total | % de las celdas | " +
      " | ".join(f"`{c}`" for c in cols) + " |")
    w("|---|---:|---:|" + "---:|" * len(cols))
    for c, n in top5:
        por_mod = " | ".join(str(modulos[m]["celdas"].get(c, 0)) for m in cols)
        w(f"| `{corto(c)}` | {n:,} | {pct(n, celdas_tot):.1f} % | {por_mod} |")
    w("")

    # Layout final
    lay = celdas_def(run)
    w("## Celdas por instancia en el layout final\n")
    if lay is None:
        w("El DEF final no esta en disco (no se versiona); correr el script en la "
          "maquina donde se hizo la corrida para obtener esta tabla.\n")
    else:
        total, por_inst = lay
        w("Cuenta de componentes del DEF final (`final/def/`) cuyo nombre empieza "
          "con el prefijo de la instancia. El total incluye buffers, celdas de "
          "reloj, tap, decap y relleno, por eso no es comparable con la sintesis.\n")
        w("| Modulo | Prefijo en el layout | Celdas | % de los componentes |")
        w("|---|---|---:|---:|")
        for mod, n in por_inst.items():
            w(f"| `{mod}` | `{INSTANCIAS[mod]}/` | {n:,} | {pct(n, total):.1f} % |")
        w(f"| Total de componentes | | {total:,} | |\n")

    w("## Metodo\n")
    w("- LibreLane aplana el diseno, salvo los modulos de "
      "`SYNTH_KEEP_HIERARCHY_MODULES` (`flow/asic_top/config.json`), que Yosys "
      "sintetiza por separado. `stat.rpt` trae una seccion por modulo con la "
      "cuenta y el area **locales** de cada uno; la suma de las secciones es el "
      "area total del top (`Chip area for top module`).")
    w("- Flip-flops = celdas `dff*` de la biblioteca `gf180mcu_fd_sc_mcu7t5v0`.")
    w("- En el layout final OpenROAD aplana el netlist, pero cada celda conserva "
      "el nombre de su instancia como prefijo.")

    texto = "\n".join(out) + "\n"
    if args.salida:
        os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)
        with open(args.salida, "w") as f:
            f.write(texto)
        print(f"-> {args.salida}")
    else:
        sys.stdout.write(texto)


if __name__ == "__main__":
    main()
