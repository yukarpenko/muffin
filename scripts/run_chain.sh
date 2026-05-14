#!/bin/bash
#PBS -l select=1:ncpus=1:mem=12gb:os=debian12
#PBS -l walltime=23:59:00
#PBS -N sims-low-energies

set -euo pipefail

# ── Locate FRAMEWORK_ROOT ──────────────────────────────────────────────────────
if [ -z "${FRAMEWORK_ROOT:-}" ]; then
  _dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [ "$_dir" != "/" ]; do
    if [ -f "$_dir/framework.env" ]; then
      source "$_dir/framework.env"; break
    fi
    _dir="$(dirname "$_dir")"
  done
fi
if [ -z "${FRAMEWORK_ROOT:-}" ]; then
  echo "ERROR: FRAMEWORK_ROOT not set." >&2; exit 1
fi

USER_DIR="${FRAMEWORK_ROOT}/user"
VHLLE="${FRAMEWORK_ROOT}/vhlle/hlle_visc"
SAMPLER="${FRAMEWORK_ROOT}/smash-hadron-sampler/build/sampler"
SMASH_BIN="${FRAMEWORK_ROOT}/smash/build/smash"
export SMASH_DIR="${FRAMEWORK_ROOT}/smash"

# ── PREFIX must be set by the caller ──────────────────────────────────────────
if [ -z "${PREFIX:-}" ]; then
  echo "ERROR: PREFIX is not set." >&2; exit 1
fi
SCENARIO_DIR="${USER_DIR}/data/${PREFIX}"
LOG_DIR="${SCENARIO_DIR}/logs"

# ── Load per-scenario run settings (stages, loops) ────────────────────────────
STAGES="hydro sampler smash"   # default
FINALSTATE_LOOPS=1             # default: sequential iterations  (was LOOPS)
FINALSTATE_PARALLEL=2          # default: parallel tasks per iteration
if [ -f "${SCENARIO_DIR}/run_settings" ]; then
  source "${SCENARIO_DIR}/run_settings"
fi

# ── Helper: is a given stage active? ──────────────────────────────────────────
stage_on() { [[ " ${STAGES} " == *" $1 "* ]]; }

echo "=== run_chain.sh: PREFIX=${PREFIX} ==="
echo "    STAGES:              ${STAGES}"
echo "    FINALSTATE_LOOPS:    ${FINALSTATE_LOOPS}"
echo "    FINALSTATE_PARALLEL: ${FINALSTATE_PARALLEL}"

# ── HYDRO ─────────────────────────────────────────────────────────────────────
if stage_on hydro; then
  mkdir -p "${SCENARIO_DIR}/hydro.output" "${LOG_DIR}"
  echo "[$(date)] Starting vHLLE... in directory $(pwd)"
  time "${VHLLE}" \
    -params "${SCENARIO_DIR}/hydro_config" \
    -outputDir "${SCENARIO_DIR}/hydro.output" \
    > "${LOG_DIR}/hydro.log" 2>&1
  cp "${SCENARIO_DIR}/hydro_config" "${SCENARIO_DIR}/hydro.output/"
  # Combine freeze-out surfaces from three fluids
  cat "${SCENARIO_DIR}/hydro.output/freezeout_p.dat" \
      "${SCENARIO_DIR}/hydro.output/freezeout_t.dat" \
      "${SCENARIO_DIR}/hydro.output/freezeout_f.dat" \
      > "${SCENARIO_DIR}/hydro.output/f.all.dat"
  echo "[$(date)] vHLLE done."
fi

# ── SAMPLER + SMASH (FINALSTATE_LOOPS sequential, FINALSTATE_PARALLEL parallel each) ──
for iseq in $(seq 1 "${FINALSTATE_LOOPS}"); do
  echo "[$(date)] Sequential iteration ${iseq}/${FINALSTATE_LOOPS}, launching ${FINALSTATE_PARALLEL} parallel tasks..."
  for ipar in $(seq 1 "${FINALSTATE_PARALLEL}"); do
  (
    iloop=$(( (iseq - 1) * FINALSTATE_PARALLEL + ipar ))
    SAMPLER_OUT="${SCENARIO_DIR}/sampler.output/${iloop}"
    SMASH_OUT="${SCENARIO_DIR}/smash.output/${iloop}"
    mkdir -p "${SAMPLER_OUT}" "${SMASH_OUT}"

    if stage_on sampler; then
      echo "[$(date)] Starting sampler (loop ${iloop})..."
      time "${SAMPLER}" --config "${SCENARIO_DIR}/sampler_config" \
        --surface "${SCENARIO_DIR}/hydro.output/f.all.dat" \
        --output  "${SAMPLER_OUT}" \
        > "${LOG_DIR}/sampler_${iloop}.log" 2>&1
      python3 "${FRAMEWORK_ROOT}/scripts/add_spectators.py" \
        --sampled_particle_list "${SAMPLER_OUT}/particle_lists.oscar" \
        --spectator_list        "${SCENARIO_DIR}/hydro.output/spectators.dat" \
        --output                "${SAMPLER_OUT}/particle_lists_0" \
        >> "${LOG_DIR}/sampler_${iloop}.log" 2>&1
    fi

    if stage_on smash; then
      echo "[$(date)] Starting SMASH (loop ${iloop})..."
      time "${SMASH_BIN}" \
        -i "${SCENARIO_DIR}/smash_config" \
        -c "Modi: { List: { File_Directory: '${SAMPLER_OUT}/' } }" \
        -o "${SMASH_OUT}/" -f \
        > "${LOG_DIR}/smash_${iloop}.log" 2>&1
      echo "[$(date)] SMASH done (loop ${iloop})."
    fi
  ) &
  done
  wait   # all FINALSTATE_PARALLEL tasks of this sequential iteration must finish
         # before the next sequential iteration starts
done
wait
echo "=== run_chain.sh: all done for PREFIX=${PREFIX} ==="
