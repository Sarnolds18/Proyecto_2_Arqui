# Pochoco SoC & Espino Core

> Meet Pochoco SoC and Espino Core. Inspired by the native flora of the Pochoco trails, it is an entry-level, highly efficient architecture designed to flourish in resource-constrained environments.

![Pochoco SoC Architecture](pochoco_soc.svg)

Welcome to the repository! This project contains the RTL for a custom 32-bit processor and its surrounding System-on-Chip (SoC) designed for FPGA deployment. The design is kept straightforward to help explore and understand computer architecture fundamentals.

This is meant to be forked, not just cloned. You'll be poking around the RTL, so make it your own, we won't judge (we might even be a little proud).

## Proyecto 3: de RTL a GDSII

La rama `proyecto3` lleva el Pochoco SoC y el juego de reflejos a un macro digital de
celdas estándar con [LibreLane](https://librelane.readthedocs.io/en/stable/) y el PDK
GF180MCU. El top del macro es `rtl/asic_top.v`: sus puertos son terminales lógicos
(reloj, reset, LEDs, botones, displays de 7 segmentos y SPI), no pads de I/O.

La versión para la FPGA (Go Board) es la entrega del Proyecto 2, tag **`p2-entrega`**.
En esta rama el RTL ya no apunta a la iCE40 (el register file de flip-flops no cabe en
la HX1K), así que las secciones *How to Build*, *Flashing from WSL* y *Power-on reset*
de más abajo describen esa versión.

### Versiones de la corrida final

| Componente | Versión |
|---|---|
| LibreLane | 3.0.16 (tag `3.0.16`) |
| PDK | `gf180mcuD`, revisión `54435919abffb937387ec956209f9cf5fd2dfbee` (instalada por LibreLane con ciel) |
| Biblioteca de celdas | `gf180mcu_fd_sc_mcu7t5v0` |
| Herramientas (dentro del `nix-shell` de LibreLane 3.0.16) | Yosys 0.62, OpenROAD `dcf36133a369abc8f3c5e5738cd4d82e4903c0e0`, Magic 8.3.623, Netgen 1.5.316, KLayout 0.30.7 |
| Corrida final | *pendiente* |

La revisión del PDK y la configuración completa de cada corrida quedan registradas en
`flow/asic_top/runs/<corrida>/resolved.json`.

### Instalar LibreLane

Guía completa en [`docs/instalacion.md`](docs/instalacion.md). En resumen (Linux o
WSL2 con systemd):

```bash
# 1. Nix con el caché binario de FOSSi (sin el caché compila todo desde cero)
curl --proto '=https' --tlsv1.2 -fsSL https://artifacts.nixos.org/nix-installer | sh -s -- install --no-confirm --extra-conf "
    extra-substituters = https://nix-cache.fossi-foundation.org
    extra-trusted-public-keys = nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs=
    extra-experimental-features = nix-command flakes
"
# 2. LibreLane 3.0.16, fuera de este repo
git clone --branch 3.0.16 https://github.com/librelane/librelane ~/librelane
cd ~/librelane && nix-shell      # la primera vez descarga ~860 MB
librelane --version              # LibreLane v3.0.16
librelane --smoke-test
```

La primera corrida con `gf180mcuD` descarga el PDK en `~/.ciel`.

En WSL2, el disco de Linux es un archivo `ext4.vhdx` dentro de C:. Nix, el PDK y las
corridas ocupan unos 15 GB, y cada corrida completa agrega ~1,3 GB más en el disco
local (casi todo son logs de STA que no se versionan). Controlar el espacio real con
`df -h /mnt/c`, no con `df -h /`. Además, usar este repo con el Git de Linux (o
`git config core.autocrlf false`): el Git de Windows convierte los archivos a CRLF y
los scripts `.sh` dejan de funcionar.

### Regenerar el programa desde `game.s`

```bash
python3 -B sw/assembler.py sw/game.s sw/game.hex --rom rtl/game_rom.v
python3 -m unittest discover -s sw -p "test_assembler.py"   # tests del assembler
python3 -B scripts/contar_palabras.py sw/game.s              # palabras de instrucción y datos
```

`--rom` genera `rtl/game_rom.v`, la ROM combinacional que usa la memoria del SoC (no se
edita a mano). Ver [`docs/memoria.md`](docs/memoria.md).

### Ejecutar la corrida final

Dentro del `nix-shell` de LibreLane (o fuera: el script entra solo), desde la raíz del
repo:

```bash
scripts/run_sweep.sh -d flow/asic_top -s final -p "100" -u "40"
```

Corre LibreLane con `flow/asic_top/config.json` (T = 100 ns, `FP_CORE_UTIL` = 40 %) y
deja todo en `flow/asic_top/runs/CP100_U40_final/`. Tarda ~6 min. El script nunca
sobrescribe una corrida existente: si el tag ya existe, la salta. Equivale a:

```bash
cd flow/asic_top
librelane --pdk gf180mcuD --run-tag CP100_U40_final -c CLOCK_PERIOD=100 -c FP_CORE_UTIL=40 config.json
python3 ../../scripts/extract_critical_paths.py runs/CP100_U40_final   # 5 peores rutas por corner
```

Resultados y análisis:

```bash
R=flow/asic_top/runs/CP100_U40_final
python3 scripts/extract_metrics.py -o results/final.csv $R       # WNS/TNS por corner, área, DRC, LVS, antena
python3 scripts/analisis_sintesis.py $R -o results/sintesis.md   # área por módulo, top-5 celdas (3.3)
python3 scripts/desglose_ruta.py $R/rutas_criticas.rpt           # ruta crítica por tramos (3.4)
```

### Simulaciones

| Testbench | Qué verifica |
|---|---|
| `sim/tb_register_file.v` | register file de flip-flops |
| `sim/tb_load_store_unit.v` | loads de byte/media palabra/palabra en todos los offsets, stores |
| `sim/tb_pochoco_periph.v` | periféricos MMIO y contador de ciclos |
| `sim/tb_game_smoke.v` | el juego completo con tiempos acortados |
| `sim/tb_game_fixed_stimuli.v` | juego con botones en ciclos fijos, RTL y netlist post-síntesis (`sim/run_fixed_stimuli.sh`, ver [`docs/simulacion_post_sintesis.md`](docs/simulacion_post_sintesis.md)) |

El comando de cada uno está en el comentario de cabecera del archivo.

### Documentación del Proyecto 3

| Archivo | Contenido |
|---|---|
| [`docs/evidencia.md`](docs/evidencia.md) | 3.1: construcciones FPGA → ASIC y la evidencia de LibreLane |
| [`docs/memoria.md`](docs/memoria.md) | 3.2: las dos estrategias de memoria |
| [`docs/timing.md`](docs/timing.md) | 3.4: barrido de `CLOCK_PERIOD`, ruta crítica y optimización |
| [`docs/simulacion_post_sintesis.md`](docs/simulacion_post_sintesis.md) | 3.7: simulación RTL vs. netlist |
| `results/*.csv` | métricas extraídas de las corridas |

## Repository Structure

The hardware is written in Verilog and divided into these main categories:

* **The Espino Core**: The central processing unit. It includes all standard pipeline stages like instruction fetch, instruction decode, an ALU for execution, a register file, a load/store unit for memory operations, and a pipeline controller. It implements [RV32E](https://docs.riscv.org/reference/isa/v20260120/unpriv/rv32.html) with a catch you might want to check out the code for.
* **The Pochoco SoC**: The top-level system wrapper. It connects the CPU core to a unified instruction/data RAM, physical board peripherals (like LEDs, switches, and displays), and an external SPI slave interface.
* **Build Files**: Constraints to map the design to the physical FPGA pins, and automation scripts for synthesis, routing, and flashing using an open-source toolchain.

## Memory Map

The SoC routes memory and data requests using a hardcoded address decoding scheme based on the highest bits of the 32-bit address.

* **`0x0000_0000` - Unified RAM**: The shared memory space for both instructions and data.
* **`0x8000_0000` - Board Peripherals**: Memory-mapped I/O for the physical board.
  * `Offset 0x00`: 7-Segment Displays
  * `Offset 0x04`: LEDs
  * `Offset 0x08`: Button Inputs (read-only)
  * `Offset 0x0C`: Cycle Counter — free-running 32-bit counter, increments every
    clock cycle from reset. Reading it returns the current count; writing any
    value to it reloads the counter to that value (write 0 to restart it from a
    known point, e.g. at the start of a timing window).
* **`0x8001_0000` - SPI Slave**: Custom SPI interface routing.
  * `Offset 0x00`: SPI Status (Chip Select state, New Data flag)
  * `Offset 0x04`: Received "Price" byte (from external master)
  * `Offset 0x08`: "Decision" byte (written by CPU to transmit)

Dive into the source code to see exactly how these components and connections are built under the hood!

## How to Build

To synthesize and program the reflex game onto the Go Board, you will need the open-source FPGA toolchain.

1. Install the tools by following the instructions at the [oss-cad-suite-build repository](https://github.com/yosyshq/oss-cad-suite-build).
2. Once installed, ~~blindly copy-paste~~ (we strongly encourage reading the Makefile first to make sure we aren't deleting your home directory) the following command in the project root to synthesize, place & route, pack and flash the bitstream:

```bash
make all
```

`TOP` defaults to `game_top` (`rtl/game_top.v`, the reflex game), so `make all` alone builds and programs the game. The Makefile also exposes the individual steps if you only need one of them:

```bash
make game_top.json   # synthesis only (yosys)
make game_top.asc    # + place & route (nextpnr-ice40)
make game_top.bin    # + pack the bitstream (icepack)
make prog             # (re-)flash an already-built game_top.bin (iceprog)
make clean             # remove build/synthesis artifacts
make TOP=pochoco_soc all   # build the bare SoC instead (e.g. to run blink.s/7seg.s)
```

`make all` (and `make prog`) always program **whatever is currently in `game_top.bin`** — if you changed `sw/game.s`, regenerate `sw/game.hex` first (see below) and then rerun `make clean && make all`, since `sw/game.hex` is baked into the bitstream via `$readmemh` at synthesis time and a stale bitstream will not pick up a newer `.hex` on its own.

### Flashing from WSL

Under WSL2 the Go Board's USB has to be passed through from Windows first (admin PowerShell, [usbipd-win](https://github.com/dorssel/usbipd-win)):

```powershell
usbipd list                        # find the FTDI device (VID 0403)
usbipd bind --busid <X-Y>          # first time only
usbipd attach --wsl --busid <X-Y>  # again after every unplug
```

If `iceprog` then reports `Can't find iCE FTDI USB device` even though `lsusb` lists `0403:6010`, your user lacks write access to the USB device. Either flash with `sudo ~/oss-cad-suite/bin/iceprog game_top.bin`, or add a udev rule once:

```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6010", MODE="0666"' | sudo tee /etc/udev/rules.d/53-goboard.rules
sudo service udev restart          # then replug + usbipd attach again
```

`iceprog` may print `flash ID: 0xFF 0xFF 0xFF 0xFF` under usbipd; as long as it ends with `VERIFY OK`, the board was programmed correctly.

## Playing the Game

The board boots straight into the game after programming (and on every power-up, since the bitstream lives in the board's flash).

1. All 4 LEDs light up for 3 seconds.
2. Then only one LED (chosen pseudo-randomly) stays on. **The reaction timer starts at this moment**, when the 4 LEDs go off; the 3-second wait is not counted.
3. Press the button that matches that LED (switch SW*i* ↔ LED D*i*, as printed on the board).
   * **Correct:** your reaction time is shown for 2 seconds on the 7-segment displays, in tenths of a second (`04` = 0.4 s, truncated), and the next round starts.
   * **Wrong button:** the displays show `EE` for about 0.5 s and the same round restarts; rounds already won are kept.
4. After 10 correct rounds the average reaction time (same unit) stays on the displays.
5. Press any button to start a new game. Unplugging and replugging the board also restarts it.

A button still held down from the previous round is ignored until it is released. Times above 9.9 s are clipped to `99`.

### Power-on reset

`pochoco_soc.v` holds the CPU in reset for 2^12 clock cycles (~164 µs) after configuration. The original 15-cycle reset let the core start before the iCE40 block RAMs (program memory and register file) returned valid data. On the board this showed up as `00` on the displays and no LEDs, while simulation, which models ideal RAM, worked fine. The counter is 13 bits wide, and its MSB is used directly as `rst_ni`, so no comparator is needed. That matters because the design uses ~98% of the HX1K's logic cells.

## Software

The `sw/` folder holds RV32E assembly programs for the Espino Core. There are two separate toolchains in play here, used for two different purposes — do not mix them up:

* **`sw/game.s` → `sw/game.hex` (the actual deliverable) — assembled with our own assembler, `sw/assembler.py`.** This is a from-scratch RV32E assembler written in plain Python 3 (standard library only, no dependencies) that does **not** invoke any external RISC-V assembler at any point, as the project requires.
* **`blink.s`, `7seg.s`, `buttons_leds.s` (earlier example/scratch programs, kept for reference) — assembled with a real RISC-V toolchain via `sw/Makefile`**, as described below. `sw/Makefile`'s generic `%.hex: %.s` rule shells out to `riscv64-unknown-elf-{as,ld,objcopy}`, so **never run `make game` (or any target matching `game.*`) inside `sw/`** — it would (re)assemble `game.hex` with that external toolchain instead of `assembler.py`, which is exactly what the project forbids for the game. Always regenerate `sw/game.hex` with the explicit command below instead.

### Regenerating `sw/game.hex` from `sw/game.s`

```bash
cd sw
python3 assembler.py game.s game.hex
```

No install step and no RISC-V toolchain needed — `assembler.py` only needs a Python 3 interpreter. It prints nothing on a clean assembly; warnings (e.g. a shift instruction, which this core executes as `ADD`, see the CATCH below) go to stderr, and any syntax/encoding error is reported compiler-style (file:line:column, with the offending source line underlined) and aborts without writing `game.hex`.

After regenerating `game.hex`, re-synthesize and reflash so the new image is actually loaded onto the FPGA:

```bash
cd ..
make clean && make all
```

To check the assembler itself (23 unit + regression tests, pure `unittest`, no external RISC-V assembler involved):

```bash
cd sw
python3 -m unittest test_assembler.py -v
```

One of those tests re-assembles `game.s` and diffs the result byte-for-byte against the committed `game.hex`, so it also doubles as a "is `game.hex` in sync with `game.s`?" check — run it after editing `game.s` and before rebuilding the bitstream.

### The other example programs (`blink.s`, `7seg.s`, `buttons_leds.s`)

These predate the reflex game and are kept only as earlier reference/scratch programs; they are **not** part of the graded deliverable and are still assembled with a real RISC-V toolchain, via `sw/Makefile`.

You'll need a RISC-V toolchain on your `PATH` (`riscv64-unknown-elf-{as,ld,objcopy}` on Debian/Ubuntu/WSL via `sudo apt install gcc-riscv64-unknown-elf`, or `brew install riscv64-unknown-elf-gcc` on macOS). If your toolchain uses a different prefix, override it on the command line rather than editing the Makefile:

```bash
cd sw
make blink                        # assembles blink.s -> blink.hex
make PREFIX=riscv64-elf- blink    # if your toolchain uses a different prefix
```

Drop a new `<name>.s` file in `sw/` and `make <name>` picks it up automatically, no `Makefile` changes needed (except for `game.s`, see above). Don't forget to change the MemFile in `pochoco_soc.v`/`game_top.v` if you want to boot a different image.

**CATCH:** The core implements [RV32E](https://docs.riscv.org/reference/isa/v20260120/unpriv/rv32.html), with one thing worth knowing: shift instructions (`SLL`/`SRL`/`SRA`/`SLLI`/`SRLI`/`SRAI`) are decoded correctly but disabled in the ALU to save LUTs on the target FPGA, so they currently execute as `ADD` instead. Avoid shifts in your assembly, or design your own shifter...
