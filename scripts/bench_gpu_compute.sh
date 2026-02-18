#!/usr/bin/env bash
set -euo pipefail

OUT_JSON="$1"
OUT_CSV="$2"
DURATION="${GPU_COMPUTE_DURATION:-60}"
TIMEOUT_SEC="${GPU_COMPUTE_TIMEOUT_SEC:-0}"
if [[ "$TIMEOUT_SEC" -le 0 ]]; then
  TIMEOUT_SEC=$(( DURATION * 4 ))
  [[ "$TIMEOUT_SEC" -lt 120 ]] && TIMEOUT_SEC=120
fi

status="ok"
bench="none"
score=""
notes=""

if command -v clpeak >/dev/null 2>&1; then
  bench="clpeak"
  tmp="$(mktemp)"
  if timeout "$TIMEOUT_SEC" clpeak >"$tmp" 2>&1; then
    # Try to capture peak single-precision FLOPS if present
    gflops="$(grep -iE 'single-precision|float' "$tmp" | grep -Eo '[0-9]+(\.[0-9]+)?\s*GFLOPS' | head -n1 | grep -Eo '[0-9]+(\.[0-9]+)?' || true)"
    score="${gflops:-}"
    notes="gflops=${gflops:-na};duration_hint=${DURATION}s"
  else
    status="failed"
    notes="clpeak execution failed"
  fi
  rm -f "$tmp"
elif command -v hashcat >/dev/null 2>&1; then
  bench="hashcat_benchmark"
  tmp="$(mktemp)"
  if timeout "$TIMEOUT_SEC" hashcat -b --machine-readable >"$tmp" 2>&1; then
    rate="$(grep -E '^SPEED' "$tmp" | head -n1 | awk -F':' '{print $6}' || true)"
    score="${rate:-}"
    notes="hashcat_rate=${rate:-na}"
  else
    status="failed"
    notes="hashcat benchmark failed"
  fi
  rm -f "$tmp"
else
  status="skipped"
  notes="No GPU compute benchmark binary found (clpeak/hashcat)."
fi

"${BENCH_PYTHON:-python3}" - "$OUT_JSON" "$status" "$bench" "$score" "$notes" <<'PY'
import json
import sys

out_json, status, bench, score, notes = sys.argv[1:6]
with open(out_json, "w") as f:
    json.dump(
        {
            "category": "gpu_compute",
            "status": status,
            "benchmark": bench,
            "primary_metric": "score",
            "score": score,
            "notes": notes,
        },
        f,
        indent=2,
    )
PY

printf "category,status,benchmark,primary_metric,score,notes\n" > "$OUT_CSV"
printf "gpu_compute,%s,%s,score,%s,%s\n" "$status" "$bench" "${score}" "${notes//,/;}" >> "$OUT_CSV"
