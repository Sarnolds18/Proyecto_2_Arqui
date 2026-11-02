# 3.2 Memoria y programa del juego

En la FPGA, el programa y los datos vivían en una RAM unificada de 512 palabras
(`pochoco_ram`), inferida como BRAM e inicializada con `$readmemh`. En el ASIC no hay BRAM
ni carga de archivo al encender (puntos 2 y 3 de 3.1), así que la memoria se reemplazó
por dos alternativas y se eligió una comparando corridas completas. Detalle y comandos en
`docs/memoria.md`.

## Palabras que usa el juego

| | Palabras | Cómo se obtuvo |
|---|---|---|
| Instrucciones | **99** (396 bytes, `0x000`–`0x188`) | `scripts/contar_palabras.py sw/game.s`: palabras que emite el assembler. Es la imagen completa del programa, se ejecuten o no todas las rutas |
| Datos | **0** | Mismo script: los 19 loads/stores de `game.s` usan como base `s0`, que solo se escribe con `lui s0, 0x80000`. Todos van a MMIO (`addr[31] = 1`) y ninguno a RAM. El assembler no acepta `.data`/`.word`, así que tampoco hay datos iniciales |

El conteo es estático y se confirmó en simulación: `sim/tb_game_fixed_stimuli.v` cuenta
durante el juego los accesos de datos a RAM (**0**) y la dirección de instrucción más alta
pedida (`0x18c`, la palabra 99). Esa última es el *prefetch* de PC+4 que hace el fetch
antes de que el salto final redirija: lee 0, que el core ejecuta como no-op.

Las dos cifras quedan bajo los límites recomendados (256 palabras de instrucciones, 64 de
datos), así que no hubo que justificar una excepción.

## El assembler genera la ROM

El assembler del Proyecto 2 (`sw/assembler.py`) ganó la opción `--rom`, que además del
`.hex` escribe el módulo Verilog de la ROM:

```bash
python3 -B sw/assembler.py sw/game.s sw/game.hex --rom rtl/game_rom.v
```

`game_rom` es combinacional: `addr_i[7:0]` es la dirección de **palabra** (256 palabras
como máximo), un `always @*` con un `case` que tiene una línea por instrucción, y
`default` = 0 (no-op). `rtl/game_rom.v` es un archivo generado, no se edita a mano. Si el
programa pasa de 256 palabras, el assembler da error en vez de truncar.

Validación: `sw/test_assembler.py` (`TestRomVerilog`) prueba el formato, el límite de 256
palabras, la línea de comandos y que la ROM de `game.s` tenga exactamente las palabras de
`game.hex` en las mismas direcciones. Además, la salida coincide con la de
`scripts/rom_provisoria.py` (un script independiente que lee el `.hex`) salvo los
comentarios de cabecera.

## Las dos estrategias

`pochoco_soc` tiene el parámetro `MemStrategy`, y `asic_top` usa `"rom"` salvo que se
defina `POCHOCO_MEM_FF`. Las dos memorias tienen la misma interfaz que la RAM original (dos
puertos con lectura sincrónica), así que el core no cambia.

| | Estrategia 1: `pochoco_mem_rom` | Estrategia 2: `pochoco_mem_ff` |
|---|---|---|
| Instrucciones | `game_rom` combinacional + registro de salida de 32 FF | 107 palabras de FF (99 de programa + 8 de datos), cargadas en el reset con la imagen de `game_rom` |
| Datos | RAM de 8 palabras de FF, sin reset, con *byte enables* | En la misma memoria, después del código |
| Arquitectura | Harvard: el puerto de datos no lee la ROM | Unificada, como la RAM del Proyecto 2 |
| Flujo | `flow/asic_top` | `flow/asic_top_ff` (`VERILOG_DEFINES: POCHOCO_MEM_FF`) |

**Por qué 8 palabras de datos si el juego usa 0.** Se deja una RAM chica, igual en las
dos estrategias, para que el SoC pueda correr programas con un poco de pila (guardar `ra`
y algunos registros en llamadas anidadas). La comparación no se ve afectada porque las dos
la tienen.

**Cómo se carga la memoria FF.** Cada palabra de programa se instancia con una dirección
constante de `game_rom` como valor de reset. Yosys reduce esas instancias a constantes: no
queda ninguna ROM en el netlist, y cada bit pasa a ser un FF con reset a 0 o con *set* a 1.
En una síntesis genérica de comprobación, los FF de tipo *set* son **1.096**, exactamente
la cantidad de bits en 1 de `game.hex`.

**Mismo comportamiento.** Con los mismos estímulos, el juego da exactamente los mismos
eventos en los mismos ciclos con las dos memorias (`sim/run_fixed_stimuli.sh rtl rom` y
`rtl ff`, comparados con `compara`: **IGUALES**).

## Comparación

Corridas `flow/asic_top/runs/CP100_U40_rom` y `flow/asic_top_ff/runs/CP100_U40_ff`, flujo
completo con T = 100 ns y `FP_CORE_UTIL` = 40 %. Las dos usan el mismo RTL y la misma
configuración; solo cambia `POCHOCO_MEM_FF`. Los números salen de `results/memoria.csv`
(`scripts/extract_metrics.py`).

| | Estrategia 1 (ROM) | Estrategia 2 (FF) | FF / ROM |
|---|---|---|---|
| Área de celdas (µm²) | **211.393** | 816.279 | 3,9× |
| Celdas estándar | 9.638 | 32.356 | 3,4× |
| Flip-flops | **1.096** | 4.265 | 3,9× |
| Utilización final | 51,6 % | 53,9 % | |
| Área del die (µm²) | **440.736** (0,44 mm²) | 1.571.020 (1,57 mm²) | 3,6× |
| Setup WS típico / lento (ns) | 64,96 / 33,30 | 56,34 / 16,09 | |
| Hold WS, peor corner (ns) | 0,152 | 0,122 | |
| Frecuencia máxima reg→reg (MHz) | **15,0** | 11,9 | |
| Violaciones de antena (redes) | 0 | 1 | |
| ¿Cierra a 100 ns / 40 %? | **sí** | **no** (antena) | |

La frecuencia máxima es 1000 / (T − WS de setup reg→reg), tomando el peor entre el corner
típico (`nom_tt_025C_5v00`) y el lento (`max_ss_125C_4v50`). Es una estimación desde una
sola corrida; el período mínimo real sale del barrido de 3.4.

Estas dos corridas son anteriores a la optimización del LSU de 3.4 y a la configuración
final (jerarquía conservada, pines, DRC de KLayout). Sirven para comparar las estrategias
entre sí con todo lo demás igual. La corrida final `CP100_U40_final` usa la ROM con el RTL
final: 196.097 µm² de celdas, 9.651 celdas y 0,4387 mm² de die.

**Por qué la FF no cierra.** Setup y hold pasan en todos los corners; lo que falla es la
antena. Después del ruteo global hay 125 redes (132 pines) con violación
(`40-openroad-checkantennas/reports/antenna_summary.rpt`). El repair las deja en 0, pero el
ruteo detallado vuelve a crear una: `net4125` → `fanout4124/I`, Metal2, razón 472,61 / 400
(`46-openroad-checkantennas-1/reports/antenna_summary.rpt`). Se podría corregir con más
iteraciones de repair o un diodo, pero no cambia la decisión.

## Elección: estrategia 1 (ROM)

- **Área y costo.** La ROM es unas 4 veces más chica en celdas, FF y die, y por lo tanto
  en costo (3.5).
- **Timing.** Tiene más margen: 33,3 ns de setup en el corner lento contra 16,1 ns.
- **Cierre.** Cierra sin intervención; la FF deja una violación de antena.

La diferencia viene de cómo se guarda un programa que no cambia. La memoria FF paga 32 FF
por palabra (la mayoría nunca se escribe) más un mux de lectura de 107 entradas en cada uno
de los dos puertos. En la ROM, esas mismas palabras son lógica combinacional que Yosys
minimiza aprovechando bits repetidos y palabras parecidas, y los 1.096 FF que quedan son
casi todos del core y los periféricos. Lo único que la FF ofrece de más es la arquitectura
unificada (un programa podría modificarse a sí mismo o usar todo el espacio para datos), y
el juego no lo usa.

El costo de la ROM es que el programa queda fijo en el silicio: cambiar `game.s` (por
ejemplo, las constantes de tiempo de 3.4) obliga a regenerar `game_rom.v` y repetir el
flujo completo.
