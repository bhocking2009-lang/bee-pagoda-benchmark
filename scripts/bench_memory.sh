#!/usr/bin/env bash
set -euo pipefail

OUT_JSON="$1"
OUT_CSV="$2"

MEM_THREADS="${MEMORY_THREADS:-0}"
[[ "$MEM_THREADS" == "0" ]] && MEM_THREADS="$(nproc)"
MEM_BLOCK_SIZE="${MEMORY_BLOCK_SIZE:-1M}"
MEM_TOTAL_SIZE="${MEMORY_TOTAL_SIZE:-8G}"

status="ok"
bench="memory_suite"
score=""
notes=()

sysbench_status="skipped"
sysbench_score=""

tiny_status="skipped"
tiny_score=""

if command -v sysbench >/dev/null 2>&1; then
  tmp="$(mktemp)"
  if sysbench memory --memory-total-size="$MEM_TOTAL_SIZE" --memory-block-size="$MEM_BLOCK_SIZE" --threads="$MEM_THREADS" run >"$tmp" 2>&1; then
    sysbench_status="ok"
    transfer="$(grep -E 'MiB transferred|transferred \(' "$tmp" | grep -Eo '[0-9]+(\.[0-9]+)? MiB/sec' | tail -n1 | awk '{print $1}' || true)"
    sysbench_score="${transfer:-}"
    notes+=("sysbench_memory_ok")
  else
    sysbench_status="failed"
    notes+=("sysbench_memory_failed")
  fi
  rm -f "$tmp"
else
  notes+=("missing_sysbench_memory")
fi

if command -v tinymembench >/dev/null 2>&1; then
  tmp="$(mktemp)"
  if tinymembench >"$tmp" 2>&1; then
    tiny_status="ok"
    tiny_bw="$(grep -E 'MB/s|MiB/s' "$tmp" | grep -Eo '[0-9]+(\.[0-9]+)?' | tail -n1 || true)"
    tiny_score="${tiny_bw:-}"
    notes+=("tinymembench_ok")
  else
    tiny_status="failed"
    notes+=("tinymembench_failed")
  fi
  rm -f "$tmp"
else
  notes+=("missing_tinymembench")
fi

if [[ "$sysbench_status" == "failed" || "$tiny_status" == "failed" ]]; then
  status="failed"
elif [[ "$sysbench_status" == "skipped" && "$tiny_status" == "skipped" ]]; then
  status="skipped"
elif [[ "$sysbench_status" == "ok" && "$tiny_status" == "skipped" ]]; then
  status="degraded"
fi

score="$sysbench_score"
notes_str="$(IFS=';'; echo "${notes[*]}")"

cat > "$OUT_JSON" <<EOF
{
  "category": "memory",
  "status": "$status",
  "benchmark": "$bench",
  "primary_metric": "read_write_mib_per_sec",
  "score": "${score}",
  "subtests": {
    "sysbench_memory": {
      "status": "$sysbench_status",
      "score": "${sysbench_score}",
      "threads": "$MEM_THREADS",
      "block_size": "$MEM_BLOCK_SIZE",
      "total_size": "$MEM_TOTAL_SIZE"
    },
    "tinymembench": {
      "status": "$tiny_status",
      "score": "${tiny_score}"
    }
  },
  "notes": "$notes_str"
}
EOF

printf "category,status,benchmark,primary_metric,score,notes\n" > "$OUT_CSV"
printf "memory,%s,%s,read_write_mib_per_sec,%s,%s\n" "$status" "$bench" "${score}" "${notes_str//,/;}" >> "$OUT_CSV"
