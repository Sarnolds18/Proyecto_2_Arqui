#!/usr/bin/env bash
# Arma el informe del Proyecto 3 en PDF a partir de las secciones en Markdown.
#
# Uso (desde cualquier carpeta del repo):
#   scripts/informe.sh [salida.pdf]          # por defecto Informe_proyecto3.pdf
#
# Junta docs/informe/metadata.yaml (portada) y docs/informe/3_*.md en orden de
# nombre, los convierte a Typst con pandoc y compila el PDF con typst. Las
# imagenes se citan desde las secciones como ../img/<archivo> (docs/img/).
#
# pandoc y typst se toman de nixpkgs con la revision fijada abajo, asi todos
# generan el PDF con las mismas versiones (pandoc 3.7.0.2, typst 0.15.1). Solo
# necesita Nix (el mismo que se usa para LibreLane); la primera vez descarga
# ~300 MB.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="$REPO/docs/informe"
SALIDA="${1:-$REPO/Informe_proyecto3.pdf}"
NIXPKGS="github:NixOS/nixpkgs/d357a2b54f0b6dc4aeb4e993190a52cf151b6f24"

if ! command -v pandoc >/dev/null || ! command -v typst >/dev/null; then
  if ! command -v nix >/dev/null; then
    . /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null || true
  fi
  exec nix shell "$NIXPKGS#pandoc" "$NIXPKGS#typst" -c "$0" "$@"
fi

shopt -s nullglob
SECCIONES=("$DIR"/3_*.md)
[ ${#SECCIONES[@]} -gt 0 ] || { echo "error: no hay secciones en $DIR" >&2; exit 1; }

echo "Secciones:"
for s in "${SECCIONES[@]}"; do echo "  ${s#$REPO/}"; done
for n in 1 2 3 4 5 6 7; do
  hay=("$DIR"/3_${n}_*.md)
  [ ${#hay[@]} -gt 0 ] || echo "  (falta la seccion 3.$n)"
done

# El .typ queda en docs/informe/ para que las rutas ../img/ de las secciones
# resuelvan a docs/img/.
TYP="$DIR/informe.typ"
trap 'rm -f "$TYP"' EXIT
pandoc "$DIR/metadata.yaml" "${SECCIONES[@]}" \
  --from markdown --to typst --standalone --toc --toc-depth 2 \
  -o "$TYP"
typst compile --root "$REPO" "$TYP" "$SALIDA"
echo "-> ${SALIDA#$REPO/}"
