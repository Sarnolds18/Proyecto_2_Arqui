#!/usr/bin/env python3
"""Capturas anotadas del layout (seccion 3.6): register file, ALU, contador de ciclos.

Uso (python del sistema, con matplotlib; klayout se toma del PATH o del
nix-shell de ~/librelane):
  python3 scripts/capturas.py flow/asic_top/runs/<corrida> -o docs/img

Genera en el directorio de salida:
  layout.png             render del GDS final con KLayout (capas del PDK)
  layout_anotado.png     el mismo render con las celdas de cada bloque coloreadas
  bloques.png            solo el contorno del core y las celdas de cada bloque
  bloques.csv            celdas, flip-flops y area por bloque

Como se identifica cada bloque. El netlist final queda aplanado, pero los
modulos de SYNTH_KEEP_HIERARCHY_MODULES (register file, ALU, contador) conservan
su prefijo de instancia (u_rf, u_alu, u_cycle_counter); el resto de las celdas
queda con nombres como _09531_. Se usan dos fuentes, en este orden:
  1. El nombre de la instancia, si conserva la jerarquia (u_..._alu...).
  2. Para los flip-flops, el nombre de la red de su salida Q, que Yosys conserva
     desde el RTL (p. ej. u_pochoco.u_core.u_rf.regs_q[2][28]).
Despues se agrega la logica combinacional exclusiva de cada bloque: una celda
pertenece al bloque si todas las celdas a las que llega su salida ya son del
bloque (cono de entrada exclusivo; se itera hasta que no cambia). Asi entran
los multiplexores de lectura/escritura del register file y el incrementador
del contador, pero no la logica compartida con otros bloques. La ALU es pura
logica combinacional: solo se identifica por el prefijo u_alu (sin
SYNTH_KEEP_HIERARCHY_MODULES no tiene flip-flops que sirvan de semilla).
"""

import argparse
import csv
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# (nombre, regex sobre el nombre de la instancia o de la red Q, color).
# Al aplanar, una red que cruza un puerto queda con uno solo de sus nombres:
# el registro de lectura B del register file (rdata_b_o) aparece como
# u_core.lsu_wdata / data_wdata (espino_id_stage: lsu_wdata_o = rf_rdata_b_i),
# y el PC del fetch como u_ram.a_addr_i, por eso la memoria lista solo sus
# registros internos.
BLOQUES = [
    ("Register file", r"u_core\.(u_rf\.|rf_rdata_[ab]\b|lsu_wdata\b)|u_pochoco\.data_wdata\b"
                      r"|\bu_rf\b", "#2a78d6"),
    ("ALU", r"\bu_alu\b", "#eb6834"),
    ("Contador de ciclos", r"u_periph\.cyc_q\b|\bu_cycle_counter\b", "#1baf7a"),
    ("Memoria (ROM/RAM)", r"g_mem_(rom|ff)\.u_ram\.(?!a_addr_i)", "#6250d6"),
]
# Celdas fisicas (relleno, taps, diodos): no son logica y no cuentan en el area.
FISICAS = re.compile(r"__(fill|fillcap|filltie|endcap|antenna)")
SALIDAS = {"Z", "ZN", "Q", "QN", "CO"}

RE_CELDA = re.compile(r"^\s*(gf180mcu_\w+)\s+(\\\S+|\w+)\s*\((.*?)\);", re.M | re.S)
RE_PIN = re.compile(r"\.(\w+)\(\s*(\\\S+|[^()\s]+)?\s*\)")
RE_COMP = re.compile(r"^\s*-\s+(\S+)\s+(\S+)\s.*?\+\s+(?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)", re.M)

RENDER_PYA = r"""
import pya
tech = pya.Technology(); tech.load(lyt)
lv = pya.LayoutView()
lv.set_config("background-color", "#ffffff")
lv.set_config("grid-visible", "false")
lv.set_config("text-visible", "false")
lv.load_layout(gds)
lv.load_layer_props(lyp)
lv.max_hier()
x1, y1, x2, y2 = [float(v) for v in box.split(",")]
lv.zoom_box(pya.DBox(x1, y1, x2, y2))
lv.save_image(out, int(w), int(h))
"""


def limpiar(nombre):
    return nombre[1:] if nombre.startswith("\\") else nombre


def leer_netlist(ruta):
    """instancia -> (celda, {pin: red})"""
    celdas = {}
    for celda, inst, pines in RE_CELDA.findall(Path(ruta).read_text()):
        celdas[limpiar(inst)] = (celda, {p: limpiar(n) for p, n in RE_PIN.findall(pines) if n})
    return celdas


def leer_lef(ruta):
    tam, actual = {}, None
    for linea in Path(ruta).read_text().splitlines():
        t = linea.split()
        if len(t) >= 2 and t[0] == "MACRO":
            actual = t[1]
        elif actual and len(t) >= 4 and t[0] == "SIZE":
            tam[actual] = (float(t[1]), float(t[3]))
    return tam


def leer_def(ruta):
    txt = Path(ruta).read_text()
    dbu = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", txt).group(1))
    die = [int(v) / dbu for v in re.search(
        r"DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)", txt).groups()]
    comps = txt[txt.index("\nCOMPONENTS"):txt.index("END COMPONENTS")]
    pos = {limpiar(n): (int(x) / dbu, int(y) / dbu) for n, _, x, y, _ in RE_COMP.findall(comps)}
    return die, pos


def es_salida(celda, pin):
    return pin in SALIDAS or (pin == "S" and "__add" in celda)


def clasificar(celdas):
    regex = [(n, re.compile(r)) for n, r, _ in BLOQUES]
    bloque = {}
    for inst, (celda, pines) in celdas.items():
        nombres = [inst] + [pines[p] for p in ("Q", "QN") if p in pines]
        for n, rx in regex:
            if any(rx.search(x) for x in nombres):
                bloque[inst] = n
                break

    # red -> instancias a las que llega
    cargas = {}
    for inst, (celda, pines) in celdas.items():
        if FISICAS.search(celda):  # un diodo de antena no cambia de quien es la red
            continue
        for p, red in pines.items():
            if not es_salida(celda, p):
                cargas.setdefault(red, set()).add(inst)

    secuenciales = {i for i, (c, _) in celdas.items() if "__dff" in c or "__latq" in c}
    cambio = True
    while cambio:
        cambio = False
        for inst, (celda, pines) in celdas.items():
            if inst in bloque or inst in secuenciales:
                continue
            destinos = set()
            for p, red in pines.items():
                if es_salida(celda, p):
                    destinos |= cargas.get(red, set())
            grupos = {bloque.get(d) for d in destinos}
            if destinos and len(grupos) == 1 and None not in grupos:
                bloque[inst] = grupos.pop()
                cambio = True
    return bloque, secuenciales


def render_klayout(cfg, gds, die, salida, ancho):
    alto = int(ancho * (die[3] - die[1]) / (die[2] - die[0]))
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(RENDER_PYA)
    cmd = ["klayout", "-b", "-r", f.name,
           "-rd", f"lyt={cfg['KLAYOUT_TECH']}", "-rd", f"lyp={cfg['KLAYOUT_PROPERTIES']}",
           "-rd", f"gds={gds}", "-rd", f"out={salida}",
           "-rd", f"box={die[0]},{die[1]},{die[2]},{die[3]}",
           "-rd", f"w={ancho}", "-rd", f"h={alto}"]
    if not shutil.which("klayout"):
        # klayout viene en el nix-shell de LibreLane; matplotlib en el python del sistema
        cmd = ["nix-shell", str(Path.home() / "librelane" / "shell.nix"), "--run",
               " ".join(shlex.quote(c) for c in cmd)]
    try:
        subprocess.run(cmd, check=True)
    finally:
        os.unlink(f.name)


def dibujar(fondo, die, rects, stats, salida, titulo):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle

    ancho_um, alto_um = die[2] - die[0], die[3] - die[1]
    fig, ax = plt.subplots(figsize=(9, 9 * alto_um / ancho_um + 1.2))
    if fondo is not None:
        ax.imshow(plt.imread(fondo), extent=(die[0], die[2], die[1], die[3]), alpha=0.45)
    else:
        ax.add_patch(Rectangle((die[0], die[1]), ancho_um, alto_um, fill=False,
                               ec="#52514e", lw=1))
    colores = {n: c for n, _, c in BLOQUES}
    for nombre, lista in rects.items():
        for x, y, w, h in lista:
            ax.add_patch(Rectangle((x, y), w, h, fc=colores[nombre], ec="none", alpha=0.85))
    # etiqueta en la mediana de cada bloque
    for nombre, lista in rects.items():
        if not lista:
            continue
        xs = sorted(x + w / 2 for x, _, w, _ in lista)
        ys = sorted(y + h / 2 for _, y, _, h in lista)
        ax.annotate(nombre, (xs[len(xs) // 2], ys[len(ys) // 2]), ha="center", va="center",
                    fontsize=10, weight="bold", color="#0b0b0b",
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=colores[nombre], lw=1.5))
    leyenda = [Patch(fc=colores[n], label=f"{n}: {stats[n]['celdas']} celdas, "
                     f"{stats[n]['area_um2']:,.0f} µm²")
               for n, _, _ in BLOQUES if stats[n]["celdas"]]
    faltan = [n for n, _, _ in BLOQUES if not stats[n]["celdas"]]
    if faltan:
        leyenda.append(Patch(fc="white", ec="#52514e",
                             label="No identificable sin jerarquía: " + ", ".join(faltan)))
    ax.legend(handles=leyenda, loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2,
              fontsize=8, frameon=False)
    ax.set_xlim(die[0], die[2])
    ax.set_ylim(die[1], die[3])
    ax.set_aspect("equal")
    ax.set_xlabel("x (µm)", fontsize=9)
    ax.set_ylabel("y (µm)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(titulo, fontsize=10)
    fig.tight_layout()
    fig.savefig(salida, dpi=200)
    plt.close(fig)
    print(f"-> {salida}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corrida", type=Path)
    ap.add_argument("-o", "--salida", type=Path, default=Path("docs/img"))
    ap.add_argument("--ancho", type=int, default=2400, help="ancho del render en pixeles")
    args = ap.parse_args()

    run = args.corrida
    cfg = json.load(open(run / "resolved.json"))
    nl = run / "final" / "nl" / f"{cfg['DESIGN_NAME']}.nl.v"
    deff = run / "final" / "def" / f"{cfg['DESIGN_NAME']}.def"
    gds = run / "final" / "gds" / f"{cfg['DESIGN_NAME']}.gds"

    celdas = leer_netlist(nl)
    tam = {}
    for lef in cfg["CELL_LEFS"]:
        tam.update(leer_lef(lef))
    die, pos = leer_def(deff)
    bloque, secuenciales = clasificar(celdas)

    rects = {n: [] for n, _, _ in BLOQUES}
    stats = {n: {"celdas": 0, "flip_flops": 0, "area_um2": 0.0} for n, _, _ in BLOQUES}
    for inst, nombre in bloque.items():
        celda = celdas[inst][0]
        w, h = tam.get(celda, (0, 0))
        stats[nombre]["celdas"] += 1
        stats[nombre]["flip_flops"] += inst in secuenciales
        stats[nombre]["area_um2"] += w * h
        if inst in pos:
            x, y = pos[inst]
            rects[nombre].append((x, y, w, h))
    logicas = [c for c, _ in celdas.values() if not FISICAS.search(c)]
    area_total = sum(tam.get(c, (0, 0))[0] * tam.get(c, (0, 0))[1] for c in logicas)

    args.salida.mkdir(parents=True, exist_ok=True)
    with open(args.salida / "bloques.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["corrida", "bloque", "celdas", "flip_flops", "area_um2", "fraccion_area"])
        for n, _, _ in BLOQUES:
            s = stats[n]
            wr.writerow([run.name, n, s["celdas"], s["flip_flops"], round(s["area_um2"], 1),
                         round(s["area_um2"] / area_total, 4) if area_total else ""])
        wr.writerow([run.name, "total (sin celdas fisicas)", len(logicas), len(secuenciales),
                     round(area_total, 1), 1])
    for n, _, _ in BLOQUES:
        s = stats[n]
        print(f"{n:20s} {s['celdas']:6d} celdas {s['flip_flops']:5d} FF "
              f"{s['area_um2']:10.1f} um2", file=sys.stderr)

    fondo = args.salida / "layout.png"
    render_klayout(cfg, gds, die, fondo, args.ancho)
    titulo = f"{cfg['DESIGN_NAME']} — {run.name}"
    dibujar(fondo, die, rects, stats, args.salida / "layout_anotado.png", titulo)
    dibujar(None, die, rects, stats, args.salida / "bloques.png", titulo + " (solo celdas de cada bloque)")


if __name__ == "__main__":
    main()
