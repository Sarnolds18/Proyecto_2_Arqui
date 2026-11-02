# Flujo obsoleto: ROM provisoria (solo dato histórico)

Este flujo se armó el 30/10 para poder correr LibreLane completo antes de que estuvieran
las estrategias de memoria de 3.2. Usaba un reemplazo provisorio de `pochoco_ram`
(`pochoco_ram.v` de esta carpeta): la ROM `game_rom` con lectura sincrónica y sin RAM de
datos.

**Ya no elabora, y es a propósito.** `pochoco_soc` dejó de instanciar `pochoco_ram`
(ahora usa `pochoco_mem_rom` o `pochoco_mem_ff`), y este `config.json` no incluye esos
módulos. Si se lanza, falla en el lint con `Unknown module type: pochoco_mem_rom`. No se
arregla: con esos módulos sería idéntico a `flow/asic_top`.

Lo que sigue valiendo:

- `runs/CP100_U40_prov/`: la primera corrida completa del SoC (30/10). Cerraba con
  setup ss 40,56 ns, 170.710 µm² de celdas y 808 FF. Sirvió para medir duración y tamaño
  en git, revisar la red de reset y probar los scripts de barrido. Se cita en
  `docs/signoff.md`.
- `scripts/rom_provisoria.py`, que genera `game_rom.v` desde `sw/game.hex` sin pasar por
  el assembler. Es un oráculo independiente del `--rom` de `sw/assembler.py` (ver
  `docs/memoria.md`).

Flujos vigentes: `flow/asic_top` (ROM, corrida final), `flow/asic_top_ff` (memoria de
flip-flops), `flow/asic_top_sim` (síntesis para la simulación post-síntesis).
