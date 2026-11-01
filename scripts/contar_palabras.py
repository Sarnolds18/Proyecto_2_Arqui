#!/usr/bin/env python3
"""Cuenta las palabras de instruccion y de datos que usa un programa (seccion 3.2).

Uso:
  python3 -B scripts/contar_palabras.py sw/game.s

Metodo (estatico, sobre la misma salida del assembler que va a la ROM):
- Instrucciones: numero de palabras que emite sw/assembler.py. Es la imagen
  completa del programa: todas las rutas, se ejecuten o no.
- Datos: el assembler no acepta .data/.word, asi que no hay datos iniciales.
  Las unicas lecturas/escrituras de memoria son loads y stores; para cada uno
  se mira el registro base. Si todo registro base se escribe solo con
  `lui rd, imm` con imm >= 0x80000 (direccion con bit 31 en 1 = MMIO, ver
  pochoco_soc.v), ningun acceso llega a la RAM y el programa usa 0 palabras
  de datos. Si algun base se calcula de otra forma, el script no puede
  acotarlo y lo dice (exit 2).

La confirmacion dinamica esta en sim/tb_game_fixed_stimuli.v, que cuenta los
accesos de datos a RAM y la direccion de instruccion mas alta ejecutada.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sw"))
import assembler as asm  # noqa: E402

MEM_FORMATS = {"LOAD", "S"}
NO_RD_FORMATS = {"S", "B"}   # formatos que no escriben un registro
MMIO_BIT = 1 << 31


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    source = sys.argv[1]
    code = asm.drop_comments(asm.code_to_list(asm.read_file(source)))
    words = asm.assemble(code)
    instructions = asm.get_instructions(code)

    writes = {}      # registro -> lista de (linea, instruccion) que lo escriben
    accesses = []    # (linea, mnemonico, offset, registro base)
    for _, line, line_no in instructions:
        mnemonic, operands = asm.tokenize(line)
        fmt = asm.INSTRUCTIONS[mnemonic][0]
        if fmt in MEM_FORMATS:
            offset, base = asm.parse_mem_operand(operands[1])
            accesses.append((line_no, mnemonic, offset, base))
        if fmt not in NO_RD_FORMATS:
            rd = asm.parse_register(operands[0])
            if rd != 0:
                writes.setdefault(rd, []).append((line_no, line.strip()))

    print(f"{source}: {len(words)} palabras de instruccion "
          f"({len(words) * 4} bytes, direcciones 0x000-0x{(len(words) - 1) * 4:03x})")
    print(f"  limite recomendado 256 palabras; la ROM tiene {asm.ROM_WORDS}")

    bases = {}       # registro base -> valor constante (o None si no es acotable)
    for _, _, _, base in accesses:
        if base in bases:
            continue
        value = None
        defs = writes.get(base, [])
        if len(defs) == 1:
            mnemonic, operands = asm.tokenize(defs[0][1])
            if mnemonic == "lui":
                value = (asm.parse_immediate(operands[1]) & 0xFFFFF) << 12
        bases[base] = value

    ram_accesses = 0
    for base, value in sorted(bases.items()):
        uses = [a for a in accesses if a[3] == base]
        offsets = sorted({a[2] for a in uses})
        if value is None:
            print(f"  x{base}: base no constante, escrita en "
                  f"{[d[0] for d in writes.get(base, [])]}: no se puede acotar")
            ram_accesses = None
            continue
        kind = "MMIO" if value & MMIO_BIT else "RAM"
        print(f"  x{base} = 0x{value:08x} ({kind}): {len(uses)} loads/stores, "
              f"offsets {offsets}")
        if kind == "RAM" and ram_accesses is not None:
            ram_accesses += len(uses)

    if ram_accesses is None:
        print("palabras de datos: no acotable estaticamente")
        return 2
    if ram_accesses:
        print(f"palabras de datos: hay {ram_accesses} accesos a RAM, revisar a mano")
        return 2
    print(f"palabras de datos: 0 ({len(accesses)} loads/stores, todos a MMIO)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
