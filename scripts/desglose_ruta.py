#!/usr/bin/env python3
"""Desglosa una ruta de rutas_criticas.rpt por tramos (seccion 3.4).

Corta la ruta en las redes con nombre jerarquico del RTL (por ejemplo
u_pochoco.u_core.lsu_addr[0]) y muestra cuanto tiempo se gasta entre una y
otra, y que parte del retardo total son celdas de retardo (dly*) insertadas
por OpenROAD como buffers.

Uso:
  python3 scripts/desglose_ruta.py flow/asic_top/runs/<corrida>/rutas_criticas.rpt \
      [-c max_ss_125C_4v50] [-t setup] [-n 1]
"""

import argparse
import re
import sys

RE_SECCION = re.compile(r"^(setup|hold) - (\S+) ")
RE_RUTA = re.compile(r"^--- ruta (\d+) de \d+ ---")
# Fanout Cap Slew Delay Time  dir  pin (celda)
RE_PIN = re.compile(r"^\s*(?:\d+\s+[\d.]+\s+)?[\d.]+\s+([\d.]+)\s+([\d.]+)\s+[\^v]\s+(\S+)\s+\((\S+)\)")
RE_NET = re.compile(r"^\s+(\S+) \(net\)$")
RE_ARRIVAL = re.compile(r"^\s+([\d.]+)\s+data arrival time")
RE_SLACK = re.compile(r"^\s+(-?[\d.]+)\s+slack")


def leer_ruta(path, chequeo, corner, n):
    seccion = ruta = None
    lineas = []
    with open(path) as f:
        for linea in f:
            m = RE_SECCION.match(linea)
            if m:
                seccion = (m.group(1), m.group(2))
                continue
            m = RE_RUTA.match(linea)
            if m:
                ruta = int(m.group(1))
                continue
            if seccion == (chequeo, corner) and ruta == n:
                lineas.append(linea.rstrip("\n"))
    return lineas


def es_nombre_rtl(net):
    # Redes del RTL: jerarquicas (u_pochoco....) y con un nombre legible,
    # no las internas de Yosys (_0123_) ni los buffers (net123).
    hoja = net.split(".")[-1].split("/")[-1]
    return net.startswith("u_pochoco.") and not re.match(r"^(_\d+_|net\d+)$", hoja)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("rpt")
    ap.add_argument("-c", "--corner", default="max_ss_125C_4v50")
    ap.add_argument("-t", "--tipo", default="setup", choices=["setup", "hold"])
    ap.add_argument("-n", "--ruta", type=int, default=1)
    args = ap.parse_args()

    lineas = leer_ruta(args.rpt, args.tipo, args.corner, args.ruta)
    if not lineas:
        sys.exit(f"error: no esta la ruta {args.ruta} de {args.tipo} en {args.corner}")

    inicio = fin = None
    for l in lineas:
        if l.startswith("Startpoint:"):
            inicio = l.split()[1]
        elif l.startswith("Endpoint:"):
            fin = l.split()[1]

    # Recorre la parte de llegada (hasta "data arrival time").
    t_prev = 0.0
    hitos = []          # (tiempo, red)
    dly_total = 0.0
    dly_n = 0
    t_clk_q = None
    arrival = slack = None
    celda_fin = None
    for l in lineas:
        m = RE_ARRIVAL.match(l)
        if m:
            arrival = float(m.group(1))
            break
        m = RE_PIN.match(l)
        if m:
            delay, t, pin, celda = float(m.group(1)), float(m.group(2)), m.group(3), m.group(4)
            t_prev = t
            celda_fin = (pin, celda)
            if pin.endswith("/CLK") and t_clk_q is None:
                t_clk_q = t
            # Salida de celda de retardo usada como buffer
            if "__dly" in celda and pin.endswith(("/Z", "/ZN")):
                dly_total += delay
                dly_n += 1
            continue
        m = RE_NET.match(l)
        if m and es_nombre_rtl(m.group(1)):
            hitos.append((t_prev, m.group(1)))
    for l in lineas:
        m = RE_SLACK.match(l)
        if m:
            slack = float(m.group(1))

    t0 = t_clk_q if t_clk_q is not None else 0.0
    puntos = [(t0, f"{inicio}/CLK (flanco de reloj en el FF de inicio)")] + hitos
    if arrival is not None:
        puntos.append((arrival, f"{fin} (entrada D del FF de fin)"))

    print(f"Ruta {args.ruta} de {args.tipo}, corner {args.corner}")
    print(f"  inicio: {inicio}")
    print(f"  fin:    {fin}  (celda {celda_fin[1] if celda_fin else '?'})")
    if slack is not None:
        print(f"  slack:  {slack:.3f} ns")
    print()
    print(f"{'llega a (ns)':>13} {'tramo (ns)':>11}  red")
    anterior = None
    for t, red in puntos:
        tramo = "" if anterior is None else f"{t - anterior:11.3f}"
        print(f"{t:13.3f} {tramo:>11}  {red}")
        anterior = t
    if arrival is not None:
        datos = arrival - t0
        print()
        print(f"Retardo de datos (desde el flanco en el FF de inicio): {datos:.3f} ns")
        print(f"Celdas de retardo (dly*) en la ruta: {dly_n}, suman {dly_total:.3f} ns "
              f"= {100 * dly_total / datos:.1f} % del retardo de datos")


if __name__ == "__main__":
    main()
