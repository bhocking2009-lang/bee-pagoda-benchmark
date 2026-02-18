#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="balanced"
CATEGORIES="all"
SKIP_PREFLIGHT=0

trim_whitespace() {
  local s="$1"
  # trim leading
  s="${s#"${s%%[![:space:]]*}"}"
  # trim trailing
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

create_unique_run_dir() {
  local base_dir="$1"
  local profile="$2"
  local ts
  ts="$(date +%Y%m%d-%H%M%S)"

  local run_dir
  local attempt
  for attempt in {1..50}; do
    local ns rand suffix
    ns="$(date +%N 2>/dev/null || echo 000000000)"
    rand="$(printf '%04x' $((RANDOM % 65536)))"
    suffix="${ns}-${rand}"
    run_dir="${base_dir}/run-${ts}-${profile}-${suffix}"
    if mkdir -p "$run_dir/raw" 2>/dev/null; then
      printf '%s' "$run_dir"
      return 0
    fi
    sleep 0.02
  done

  echo "[ERROR] Unable to create unique run directory under ${base_dir}" >&2
  return 1
}

resolve_python_bin() {
  if [[ -n "${BENCH_PYTHON:-}" ]]; then
    echo "$BENCH_PYTHON"
    return 0
  fi

  if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    echo "${VIRTUAL_ENV}/bin/python"
    return 0
  fi

  local venv_candidate
  for venv_candidate in "$ROOT/.venv/bin/python" "$ROOT/.venv312/bin/python"; do
    if [[ -x "$venv_candidate" ]]; then
      echo "$venv_candidate"
      return 0
    fi
  done

  command -v python3
}

usage() {
  cat <<EOF
Usage:
  ./run_suite.sh [profile] [categories] [--skip-preflight] [--python /path/to/python]
  ./run_suite.sh [profile] --categories cpu,gpu,ai,memory,disk [--skip-preflight] [--python /path/to/python]

Examples:
  ./run_suite.sh balanced
  ./run_suite.sh quick cpu,memory,disk
  ./run_suite.sh deep --categories cpu,gpu
  ./run_suite.sh quick ai --skip-preflight
  ./run_suite.sh balanced --categories ai --python ./.venv/bin/python
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -n "${1:-}" && "${1:-}" != --* ]]; then
  PROFILE="$1"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --categories)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --categories requires a value" >&2
        exit 2
      fi
      CATEGORIES="${2:-}"
      shift 2
      ;;
    --skip-preflight)
      SKIP_PREFLIGHT=1
      shift
      ;;
    --python)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --python requires a path" >&2
        exit 2
      fi
      BENCH_PYTHON="${2:-}"
      if [[ -z "$BENCH_PYTHON" ]]; then
        echo "[ERROR] --python requires a path" >&2
        exit 2
      fi
      shift 2
      ;;
    --*)
      echo "[ERROR] Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      if [[ "$CATEGORIES" == "all" ]]; then
        CATEGORIES="$1"
      else
        echo "[ERROR] Unexpected argument: $1" >&2
        usage
        exit 2
      fi
      shift
      ;;
  esac
done

PROFILE_FILE="$ROOT/profiles/${PROFILE}.env"
if [[ ! -f "$PROFILE_FILE" ]]; then
  echo "[ERROR] Profile not found: $PROFILE_FILE" >&2
  echo "Available profiles:" >&2
  ls -1 "$ROOT/profiles" | sed 's/.env$//' >&2
  exit 2
fi

# Load profile defaults without overriding explicit environment overrides.
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "${line//[[:space:]]/}" ]] && continue
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
    key="${BASH_REMATCH[1]}"
    raw_val="${BASH_REMATCH[2]}"
    # Trim surrounding whitespace from value (profile files use simple KEY=VALUE form).
    raw_val="${raw_val#${raw_val%%[![:space:]]*}}"
    raw_val="${raw_val%${raw_val##*[![:space:]]}}"
    if [[ -z "${!key+x}" ]]; then
      printf -v "$key" '%s' "$raw_val"
      export "$key"
    fi
  fi
done < "$PROFILE_FILE"

BENCH_PYTHON="$(resolve_python_bin)"
if [[ -z "$BENCH_PYTHON" || ! -x "$BENCH_PYTHON" ]]; then
  echo "[ERROR] Python interpreter not executable: ${BENCH_PYTHON:-<none>}" >&2
  exit 2
fi
export BENCH_PYTHON
echo "[INFO] Python interpreter: $BENCH_PYTHON"

RUN_DIR="$(create_unique_run_dir "$ROOT/reports" "$PROFILE")"
RAW_DIR="$RUN_DIR/raw"

SELECTED=()
if [[ "$CATEGORIES" == "all" || -z "$CATEGORIES" ]]; then
  SELECTED=(cpu gpu_compute gpu_game ai memory disk)
else
  IFS=',' read -r -a REQUESTED <<< "$CATEGORIES"
  for c in "${REQUESTED[@]}"; do
    c="$(trim_whitespace "$c")"
    [[ -z "$c" ]] && continue
    case "$c" in
      cpu) SELECTED+=(cpu) ;;
      gpu) SELECTED+=(gpu_compute gpu_game) ;;
      ai) SELECTED+=(ai) ;;
      memory) SELECTED+=(memory) ;;
      disk|storage) SELECTED+=(disk) ;;
      *)
        echo "[ERROR] Unknown category: $c" >&2
        usage
        exit 2
        ;;
    esac
  done
fi

if [[ ${#SELECTED[@]} -eq 0 ]]; then
  echo "[ERROR] No benchmark categories selected. Use --categories cpu,gpu,ai,memory,disk" >&2
  exit 2
fi

# de-duplicate while preserving order
DEDUP=()
for item in "${SELECTED[@]}"; do
  skip=0
  for d in "${DEDUP[@]:-}"; do
    [[ "$d" == "$item" ]] && skip=1 && break
  done
  [[ $skip -eq 0 ]] && DEDUP+=("$item")
done
SELECTED=("${DEDUP[@]}")

exit_code=0

if [[ "$SKIP_PREFLIGHT" == "1" ]]; then
  "$BENCH_PYTHON" - "$RAW_DIR/preflight.json" "$RAW_DIR/preflight.csv" <<'PY'
import csv
import json
import sys
from datetime import datetime, timezone

out_json, out_csv = sys.argv[1], sys.argv[2]
summary = {
    "category": "preflight",
    "status": "skipped",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "status_counts": {"present": 0, "missing": 0, "version-mismatch": 0, "optional-missing": 0},
    "checks": [],
    "interpreter": sys.executable,
    "notes": "preflight skipped via --skip-preflight",
}
with open(out_json, "w") as f:
    json.dump(summary, f, indent=2)
with open(out_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["name", "type", "required", "status", "version", "min_version", "path", "notes"])
    w.writerow(["preflight", "meta", False, "skipped", "", "", "", summary["notes"]])
PY
else
  echo "[INFO] Running preflight checks..."
  if ! "$ROOT/scripts/preflight_check.sh" "$RAW_DIR/preflight.json" "$RAW_DIR/preflight.csv" >/dev/null; then
    echo "[ERROR] preflight check script execution failed" >&2
    exit_code=1
  fi
fi

run_step() {
  local name="$1"
  local script="$2"
  echo "[INFO] Running $name..."
  if ! "$script" "$RAW_DIR/${name}.json" "$RAW_DIR/${name}.csv"; then
    echo "[ERROR] $name step failed" >&2
    exit_code=1
  fi
}

RUN_REPS="${RUN_REPETITIONS:-1}"
if ! [[ "$RUN_REPS" =~ ^[0-9]+$ ]] || [[ "$RUN_REPS" -lt 1 ]]; then
  echo "[ERROR] RUN_REPETITIONS must be a positive integer (got: $RUN_REPS)" >&2
  exit 2
fi

for ((i=1; i<=RUN_REPS; i++)); do
  echo "[INFO] Repetition $i/$RUN_REPS"
  for step in "${SELECTED[@]}"; do
    case "$step" in
      cpu) run_step cpu "$ROOT/scripts/bench_cpu.sh" ;;
      gpu_compute) run_step gpu_compute "$ROOT/scripts/bench_gpu_compute.sh" ;;
      gpu_game) run_step gpu_game "$ROOT/scripts/bench_gpu_game.sh" ;;
      ai) run_step ai "$ROOT/scripts/bench_ai.sh" ;;
      memory) run_step memory "$ROOT/scripts/bench_memory.sh" ;;
      disk) STORAGE_WORKDIR="$RUN_DIR" run_step disk "$ROOT/scripts/bench_storage.sh" ;;
    esac
  done
done

REPORT_PATH_TMP="$(mktemp)"
trap 'rm -f "$REPORT_PATH_TMP"' EXIT
"$BENCH_PYTHON" "$ROOT/scripts/generate_report.py" "$RUN_DIR" "$PROFILE" "$(IFS=,; echo "${SELECTED[*]}")" >"$REPORT_PATH_TMP"
REPORT_MD="$(cat "$REPORT_PATH_TMP")"

# enforce status-based exit behavior from selected scope
if grep -R '"status": "failed"' "$RAW_DIR"/*.json >/dev/null 2>&1; then
  exit_code=1
fi

echo "[OK] Report: $REPORT_MD"
exit "$exit_code"
