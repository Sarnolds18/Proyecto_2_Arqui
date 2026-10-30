#!/usr/bin/env python3
"""ROM provisoria: convierte un .hex (una palabra de 32 bits por linea) en el
modulo combinacional game_rom con el formato acordado para rtl/game_rom.v.

Uso:
  python3 scripts/rom_provisoria.py sw/game.hex rtl/game_rom.v

PROVISORIO: el enunciado pide que la ROM la genere el assembler desde game.s
(sw/assembler.py). Este script existe para poder correr el flujo mientras tanto
y como referencia independiente: la salida del assembler debe tener el mismo
contenido (mismas palabras en las mismas direcciones).
"""

import sys
from pathlib import Path

ADDR_BITS = 8                 # direccion de palabra: hasta 256 palabras
MAX_WORDS = 1 << ADDR_BITS


def leer_hex(ruta):
    palabras = []
    for n, linea in enumerate(Path(ruta).read_text().splitlines(), 1):
        linea = linea.split("//")[0].strip()
        if not linea:
            continue
        if len(linea) != 8:
            sys.exit(f"{ruta}:{n}: se esperaba una palabra de 8 digitos hex, hay '{linea}'")
        try:
            palabras.append(int(linea, 16))
        except ValueError:
            sys.exit(f"{ruta}:{n}: '{linea}' no es hexadecimal")
    if len(palabras) > MAX_WORDS:
        sys.exit(f"{ruta}: {len(palabras)} palabras, el maximo es {MAX_WORDS}")
    return palabras


def generar(palabras, origen):
    lineas = [
        "// game_rom: imagen del programa como ROM combinacional.",
        "// ARCHIVO GENERADO, no editar a mano.",
        f"// PROVISORIA: generada desde {origen} por scripts/rom_provisoria.py.",
        "// Se reemplaza por la salida de sw/assembler.py (debe dar el mismo contenido).",
        "",
        "module game_rom (",
        f"  input  wire [{ADDR_BITS - 1}:0]  addr_i,  // direccion de palabra",
        "  output reg  [31:0] data_o",
        ");",
        "",
        "  always @* begin",
        "    case (addr_i)",
    ]
    for i, w in enumerate(palabras):
        lineas.append(f"      {ADDR_BITS}'d{i}: data_o = 32'h{w:08x};")
    lineas += [
        "      default: data_o = 32'h00000000;",
        "    endcase",
        "  end",
        "",
        "endmodule",
        "",
    ]
    return "\n".join(lineas)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    origen, destino = sys.argv[1], sys.argv[2]
    palabras = leer_hex(origen)
    Path(destino).write_text(generar(palabras, origen))
    print(f"{len(palabras)} palabras -> {destino}", file=sys.stderr)


if __name__ == "__main__":
    main()
