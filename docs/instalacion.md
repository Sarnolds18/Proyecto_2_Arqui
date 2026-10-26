# Instalación de LibreLane (Proyecto 3)

Flujo RTL → GDSII con [LibreLane](https://librelane.readthedocs.io/en/stable/) y el PDK
GF180MCU (`gf180mcuD`), instalado con Nix. Probado en Ubuntu sobre WSL2 (Windows), con
systemd activo (`/etc/wsl.conf` → `[boot] systemd=true`).

Guía oficial:
<https://librelane.readthedocs.io/en/stable/installation/nix_installation/installation_win.html>

## 1. Instalar Nix con el caché binario de FOSSi

Sin el caché, Nix compila todas las herramientas desde cero (horas). No usar
`sudo apt install nix-bin`: es una versión antigua y no configura el caché.

```bash
sudo apt-get install -y curl
curl --proto '=https' --tlsv1.2 -fsSL https://artifacts.nixos.org/nix-installer | sh -s -- install --no-confirm --extra-conf "
    extra-substituters = https://nix-cache.fossi-foundation.org
    extra-trusted-public-keys = nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs=
    extra-experimental-features = nix-command flakes
"
```

Después abrir una terminal nueva (o `. /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh`)
y comprobar con `nix --version`.

## 2. Clonar LibreLane y entrar al entorno

LibreLane va fuera de este repo:

```bash
git clone https://github.com/librelane/librelane ~/librelane
cd ~/librelane
nix-shell
```

La primera vez descarga ~860 MB (~5 GB descomprimidos). El prompt cambia a
`[nix-shell:~/librelane]$`. Todas las herramientas del flujo (Yosys, OpenROAD, Magic,
Netgen, KLayout, iverilog) están disponibles solo dentro de este shell.

Al entrar aparece `error: file 'nixpkgs' was not found in the Nix search path` seguido
de `uses bash from your environment`. Es inofensivo: solo afecta qué bash usa el shell.

## 3. Verificar la instalación

```bash
librelane --smoke-test
```

Corre un diseño de prueba con sky130 y debe terminar en `Smoke test passed.`

Prueba con GF180 (ejemplo PM32 del tutorial de LibreLane):

```bash
mkdir -p ~/pm32_test/src
cp ~/librelane/docs/source/getting_started/newcomers/{pm32.v,spm.v} ~/pm32_test/src/
cat > ~/pm32_test/config.json <<'EOF'
{
  "DESIGN_NAME": "pm32",
  "VERILOG_FILES": ["dir::src/pm32.v", "dir::src/spm.v"],
  "CLOCK_PORT": "clk",
  "CLOCK_PERIOD": 100,
  "FP_CORE_UTIL": 40
}
EOF
cd ~/pm32_test
librelane --pdk gf180mcuD config.json
```

La primera corrida descarga el PDK en `~/.ciel`. Debe terminar en `Flow complete.` con
Antenna, LVS y DRC en `Passed`.

## Versiones instaladas

Las versiones definitivas de la corrida final se registran en el README.

| Componente | Versión |
|---|---|
| LibreLane | 3.0.16 |
| PDK | `gf180mcuD`, revisión `54435919abffb937387ec956209f9cf5fd2dfbee` (ciel) |
| Biblioteca de celdas | `gf180mcu_fd_sc_mcu7t5v0` |
| OpenROAD | 2026-02-17 |
| Yosys | 0.62 |
| Magic | 8.3.623 |
| Netgen | 1.5.316 |
| KLayout | 0.30.7 |
| ciel | 2.4.0 |

## Notas del flujo con `gf180mcuD`

- LibreLane analiza 9 corners: parásitos `nom`/`min`/`max` ×
  `tt_025C_5v00`/`ss_125C_4v50`/`ff_n40C_5v50`.
- El paso `KLayout.DRC` se salta porque `KLAYOUT_DRC_RUNSET` no está definido para este
  PDK; el DRC reportado proviene de Magic (`magic__drc_error__count`).
- Las métricas de cada corrida quedan en `runs/<corrida>/final/metrics.json`, y los
  reportes de STA por corner en `runs/<corrida>/NN-openroad-stapostpnr/<corner>/`.
