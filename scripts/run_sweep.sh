#!/usr/bin/env bash
# Barrido de corridas de LibreLane sobre flow/asic_top: una corrida por cada
# combinacion de CLOCK_PERIOD x FP_CORE_UTIL, con tag CP<T>_U<U>_<sufijo>.
#
# Uso:
#   scripts/run_sweep.sh -s <sufijo> -p "<periodos ns>" -u "<utilizaciones %>" \
#                        [-c KEY=VAL ...] [-- <args extra de librelane>]
#
# Ejemplos:
#   scripts/run_sweep.sh -s rom -p "100" -u "40"
#   scripts/run_sweep.sh -s rom -p "100 50 40 30" -u "40"
#   scripts/run_sweep.sh -s rom -p "100" -u "30 40 50 60" -- --to OpenROAD.GlobalRouting
#
# Un tag que ya existe en runs/ se salta (nunca se sobrescribe una corrida).
# Si una corrida falla se sigue con la siguiente; al final se imprime un
# resumen y el comando para extraer las metricas a CSV.

set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLOW_DIR="$REPO/flow/asic_top"
LIBRELANE_DIR="${LIBRELANE_DIR:-$HOME/librelane}"
PDK="${PDK:-gf180mcuD}"

uso() { sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-1}"; }

SUFIJO="" PERIODOS="" UTILS=""
OVERRIDES=()
while getopts "s:p:u:c:h" opt; do
  case "$opt" in
    s) SUFIJO="$OPTARG" ;;
    p) PERIODOS="$OPTARG" ;;
    u) UTILS="$OPTARG" ;;
    c) OVERRIDES+=(-c "$OPTARG") ;;
    h) uso 0 ;;
    *) uso ;;
  esac
done
shift $((OPTIND - 1))
[ "${1:-}" = "--" ] && shift
EXTRA=("$@")

[ -n "$SUFIJO" ] && [ -n "$PERIODOS" ] && [ -n "$UTILS" ] || uso

# LibreLane vive en el nix-shell de ~/librelane: si no esta en el PATH, se
# vuelve a ejecutar este mismo script dentro de ese shell.
if ! command -v librelane >/dev/null 2>&1; then
  if [ -n "${IN_SWEEP_NIX_SHELL:-}" ]; then
    echo "error: librelane no esta disponible ni dentro de nix-shell" >&2; exit 1
  fi
  NIX_PROFILE=/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
  [ -f "$NIX_PROFILE" ] && . "$NIX_PROFILE"
  exec env IN_SWEEP_NIX_SHELL=1 nix-shell "$LIBRELANE_DIR/shell.nix" \
    --run "$(printf '%q ' "${BASH_SOURCE[0]}" -s "$SUFIJO" -p "$PERIODOS" -u "$UTILS" \
             "${OVERRIDES[@]}" -- "${EXTRA[@]}")"
fi

cd "$FLOW_DIR" || exit 1
mkdir -p runs

declare -a RESUMEN=()
for T in $PERIODOS; do
  for U in $UTILS; do
    TAG="CP${T}_U${U}_${SUFIJO}"
    if [ -e "runs/$TAG" ]; then
      RESUMEN+=("$TAG  SALTADA (ya existe)")
      continue
    fi
    echo "=== $TAG: CLOCK_PERIOD=$T FP_CORE_UTIL=$U ==="
    INICIO=$(date +%s)
    librelane --pdk "$PDK" --run-tag "$TAG" \
      -c "CLOCK_PERIOD=$T" -c "FP_CORE_UTIL=$U" "${OVERRIDES[@]}" \
      "${EXTRA[@]}" config.json
    RC=$?
    DUR=$(( $(date +%s) - INICIO ))
    if [ $RC -eq 0 ]; then
      RESUMEN+=("$TAG  OK (${DUR} s)")
    else
      RESUMEN+=("$TAG  FALLO rc=$RC (${DUR} s), ver runs/$TAG/flow.log")
    fi
  done
done

echo
echo "=== Resumen del barrido ==="
printf '%s\n' "${RESUMEN[@]}"
echo
echo "Metricas: python3 scripts/extract_metrics.py -o results/<nombre>.csv flow/asic_top/runs/CP*_${SUFIJO}"
