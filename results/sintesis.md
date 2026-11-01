# Analisis de sintesis: `CP100_U40_final`

Fuente: `flow/asic_top/runs/CP100_U40_final/06-yosys-synthesis/reports/stat.rpt` (generado por `scripts/analisis_sintesis.py`).

## Area por modulo

Areas de celdas de la sintesis (antes de place & route: sin buffers de repair, CTS, tap ni relleno). Para el top, el area es **local** (sin los submodulos), es decir, todo lo que se aplano en el top.

| Modulo | Instancia | Area (um2) | % del total | Celdas | Flip-flops | % secuencial |
|---|---|---:|---:|---:|---:|---:|
| `asic_top` | `(top, resto del SoC)` | 77,616 | 47.4 % | 3,090 | 522 | 45.7 % |
| `espino_register_file` | `u_pochoco.u_core.u_rf` | 71,588 | 43.7 % | 1,804 | 544 | 56.7 % |
| `espino_alu` | `u_pochoco.u_core.u_id.u_alu` | 10,006 | 6.1 % | 580 | 0 | 0.0 % |
| `pochoco_cycle_counter` | `u_pochoco.u_periph.u_cycle_counter` | 4,632 | 2.8 % | 162 | 32 | 51.6 % |
| **Total** | | **163,841** | 100 % | **5,636** | **1,098** | |

Modulo con mas area (de los que se conservan): **`espino_register_file`**, 71,588 um2 (43.7 %).

Contador de ciclos (`pochoco_cycle_counter`): **4,632 um2 = 2.83 % del area de celdas**.

## Las 5 celdas mas usadas

Cantidad total en el diseno y cuantas hay en cada modulo.

| Celda | Total | % de las celdas | `asic_top` | `espino_register_file` | `espino_alu` | `pochoco_cycle_counter` |
|---|---:|---:|---:|---:|---:|---:|
| `nand2_1` | 976 | 17.3 % | 713 | 142 | 82 | 39 |
| `dffrnq_1` | 776 | 13.8 % | 200 | 544 | 0 | 32 |
| `aoi22_1` | 615 | 10.9 % | 222 | 384 | 9 | 0 |
| `mux2_2` | 554 | 9.8 % | 72 | 480 | 0 | 2 |
| `oai21_1` | 439 | 7.8 % | 373 | 0 | 51 | 15 |

## Celdas por instancia en el layout final

El DEF final no esta en disco (no se versiona); correr el script en la maquina donde se hizo la corrida para obtener esta tabla.

## Metodo

- LibreLane aplana el diseno, salvo los modulos de `SYNTH_KEEP_HIERARCHY_MODULES` (`flow/asic_top/config.json`), que Yosys sintetiza por separado. `stat.rpt` trae una seccion por modulo con la cuenta y el area **locales** de cada uno; la suma de las secciones es el area total del top (`Chip area for top module`).
- Flip-flops = celdas `dff*` de la biblioteca `gf180mcu_fd_sc_mcu7t5v0`.
- En el layout final OpenROAD aplana el netlist, pero cada celda conserva el nombre de su instancia como prefijo.
