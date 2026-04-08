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

export LC_ALL=C

PYTHON_BIN="${BENCH_PYTHON:-python3}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

status="ok"
bench="none"
score=""
notes=""

# Detect GPU vendor metadata via gpu_provider.py
gpu_meta="{}"
if [[ -f "$ROOT_DIR/gpu_provider.py" ]]; then
  gpu_meta="$("$PYTHON_BIN" - "$ROOT_DIR" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import json
try:
    from gpu_provider import detect_metadata
    print(json.dumps(detect_metadata()))
except Exception as e:
    print(json.dumps({"vendor_detected": "unknown", "provider_selected": "GenericProvider", "provider_mode": "generic_fallback", "error": str(e)}))
PY
)"
fi

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

"${BENCH_PYTHON:-python3}" - "$OUT_JSON" "$status" "$bench" "$score" "$notes" "$gpu_meta" <<'PY'
import json
import sys

out_json, status, bench, score, notes, gpu_meta_str = sys.argv[1:7]
try:
    gpu_meta = json.loads(gpu_meta_str)
except Exception:
    gpu_meta = {}
with open(out_json, "w") as f:
    json.dump(
        {
            "category": "gpu_compute",
            "status": status,
            "benchmark": bench,
            "primary_metric": "score",
            "score": score,
            "notes": notes,
            "vendor_detected": gpu_meta.get("vendor_detected", "unknown"),
            "provider_selected": gpu_meta.get("provider_selected", "GenericProvider"),
            "provider_mode": gpu_meta.get("provider_mode", "generic_fallback"),
            "gpu_enrichment": {k: v for k, v in gpu_meta.items()
                               if k not in ("vendor_detected", "provider_selected", "provider_mode")},
        },
        f,
        indent=2,
    )
PY

printf "category,status,benchmark,primary_metric,score,notes\n" > "$OUT_CSV"
printf "gpu_compute,%s,%s,score,%s,%s\n" "$status" "$bench" "${score}" "${notes//,/;}" >> "$OUT_CSV"
