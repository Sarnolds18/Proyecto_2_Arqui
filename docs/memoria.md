# 3.2 Memoria y programa del juego

## Palabras que usa el juego

| | Palabras | Cómo se obtuvo |
|---|---|---|
| Instrucciones | **99** (396 bytes, `0x000`–`0x188`) | `python3 -B scripts/contar_palabras.py sw/game.s`: número de palabras que emite el assembler (la imagen completa, todas las rutas) |
| Datos | **0** | Mismo script: los 19 loads/stores de `game.s` usan como base `s0`, que solo se escribe con `lui s0, 0x80000` → todos van a MMIO (`addr[31] = 1`), ninguno a RAM. El assembler no acepta `.data/.word`, así que no hay datos iniciales |

Confirmación dinámica: `sim/run_fixed_stimuli.sh rtl` cuenta, durante la simulación del
juego, los accesos de datos a RAM (**0**) y la dirección de instrucción más alta pedida
(`0x18c` = palabra 99: es el prefetch de PC+4 que hace el fetch antes de que el salto
final redirija; lee 0, que el core ejecuta como no-op).

Ambos números quedan bajo los límites recomendados (256 instrucciones, 64 datos).

## El assembler genera la ROM

```bash
python3 -B sw/assembler.py sw/game.s sw/game.hex --rom rtl/game_rom.v
```

`--rom` escribe además el módulo `game_rom` (formato acordado: `addr_i[7:0]` = dirección
de palabra, `always @*` + `case`, `default` = 0). `rtl/game_rom.v` es un archivo generado.
Tests en `sw/test_assembler.py` (`TestRomVerilog`): formato, límite de 256 palabras, CLI y
que la ROM de `game.s` tenga exactamente las palabras de `game.hex` en las mismas
direcciones. Con el `game.s` del Proyecto 2 la salida es idéntica a la ROM provisoria de
`scripts/rom_provisoria.py` salvo los comentarios de cabecera.

## Las dos estrategias

`pochoco_soc` tiene el parámetro `MemStrategy`; `asic_top` usa `"rom"` salvo que se
defina `POCHOCO_MEM_FF`. Las dos tienen la misma interfaz que la RAM original (dos
puertos con lectura sincrónica), así que el core no cambia. En la simulación del juego
las dos dan **exactamente los mismos eventos en los mismos ciclos**
(`sim/run_fixed_stimuli.sh rtl rom` vs `rtl ff`, comparados con `compara`).

| | Estrategia 1: `pochoco_mem_rom` | Estrategia 2: `pochoco_mem_ff` |
|---|---|---|
| Instrucciones | `game_rom` combinacional + registro de salida de 32 FF | 107 palabras de FF (99 de programa + 8 de datos), cargadas en el reset desde `game_rom` con direcciones constantes |
| Datos | RAM de 8 palabras de FF, sin reset, con byte enables | En la misma memoria, después del código |
| Arquitectura | Harvard (el puerto de datos no lee la ROM) | Unificada, como la RAM del Proyecto 2 |
| Flujo de LibreLane | `flow/asic_top` | `flow/asic_top_ff` (`VERILOG_DEFINES: POCHOCO_MEM_FF`) |

8 palabras de datos: el juego usa 0. Se deja una RAM chica (y la misma capacidad en las
dos estrategias) para que el SoC siga pudiendo correr programas con algo de pila (por ejemplo,
guardar `ra` y algunos registros en llamadas anidadas).

Chequeo previo con Yosys genérico (`synth -flatten`, **no** son números para el informe):
estrategia 1: 1.096 FF en total; estrategia 2: 4.265 FF. En la estrategia 2 la memoria
son 3.424 FF (107 × 32) y **1.096 de ellos son de tipo set**, exactamente la cantidad de
bits en 1 de `game.hex`: las instancias de `game_rom` se reducen a constantes y no queda
ROM.

## Comparación (M6) — pendiente de las corridas

```bash
scripts/run_sweep.sh -s rom -p "100" -u "40"
scripts/run_sweep.sh -d flow/asic_top_ff -s ff -p "100" -u "40"
python3 scripts/extract_metrics.py -o results/memoria.csv \
  flow/asic_top/runs/CP100_U40_rom flow/asic_top_ff/runs/CP100_U40_ff
```

| | Estrategia 1 (ROM) | Estrategia 2 (FF) |
|---|---|---|
| Área de celdas (µm²) | pendiente | pendiente |
| Flip-flops | pendiente | pendiente |
| Utilización | pendiente | pendiente |
| Frecuencia máxima (MHz) | pendiente | pendiente |
| ¿Cierra a 100 ns / 40 %? | pendiente | pendiente |
