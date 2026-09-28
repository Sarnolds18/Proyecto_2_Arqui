# Pochoco SoC & Espino Core

> Meet Pochoco SoC and Espino Core. Inspired by the native flora of the Pochoco trails, it is an entry-level, highly efficient architecture designed to flourish in resource-constrained environments.

![Pochoco SoC Architecture](pochoco_soc.svg)

Welcome to the repository! This project contains the RTL for a custom 32-bit processor and its surrounding System-on-Chip (SoC) designed for FPGA deployment. The design is kept straightforward to help explore and understand computer architecture fundamentals.

This is meant to be forked, not just cloned. You'll be poking around the RTL, so make it your own, we won't judge (we might even be a little proud).

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
