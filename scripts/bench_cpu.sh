#!/usr/bin/env bash
set -euo pipefail

OUT_JSON="$1"
OUT_CSV="$2"

DURATION="${CPU_DURATION:-60}"
THREADS="${CPU_THREADS:-0}"
[[ "$THREADS" == "0" ]] && THREADS="$(nproc)"

CPU_COMPRESS_DURATION="${CPU_COMPRESS_DURATION:-20}"
CPU_ENCODE_DURATION="${CPU_ENCODE_DURATION:-20}"

status="ok"
bench="cpu_suite"
score=""
notes=()

baseline_status="skipped"
baseline_tool="none"
baseline_score=""

compress_status="skipped"
compress_tool="none"
compress_score=""

encode_status="skipped"
encode_tool="none"
encode_score=""

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

# Baseline: sysbench -> openssl fallback
if command -v sysbench >/dev/null 2>&1; then
  baseline_tool="sysbench"
  tmp="$(mktemp)"
  if sysbench cpu --threads="$THREADS" --time="$DURATION" run >"$tmp" 2>&1; then
    baseline_status="ok"
    eps="$(grep -E 'events per second:' "$tmp" | awk '{print $4}' | tail -n1)"
    baseline_score="${eps:-}"
    notes+=("baseline=sysbench")
  else
    baseline_status="failed"
    notes+=("baseline_sysbench_failed")
  fi
  rm -f "$tmp"
elif command -v openssl >/dev/null 2>&1; then
  baseline_tool="openssl_speed"
  tmp="$(mktemp)"
  if openssl speed -seconds "$DURATION" -multi "$THREADS" sha256 >"$tmp" 2>&1; then
    baseline_status="degraded"
    line="$(grep -E '^sha256 ' "$tmp" | tail -n1 || true)"
    baseline_score="$(echo "$line" | awk '{print $NF}')"
    notes+=("baseline=openssl_fallback")
  else
    baseline_status="failed"
    notes+=("baseline_openssl_failed")
  fi
  rm -f "$tmp"
else
  notes+=("baseline_missing_sysbench_openssl")
fi

# Compression: 7z benchmark
if command -v 7z >/dev/null 2>&1; then
  compress_tool="7z_b"
  tmp="$(mktemp)"
  if 7z b -mmt="$THREADS" >"$tmp" 2>&1; then
    compress_status="ok"
    rating="$(grep -E 'Tot:.*MIPS|Tot:' "$tmp" | tail -n1 | grep -Eo '[0-9]+' | tail -n1 || true)"
    compress_score="${rating:-}"
    notes+=("compression=7z")
  else
    compress_status="failed"
    notes+=("compression_7z_failed")
  fi
  rm -f "$tmp"
else
  notes+=("compression_missing_7z")
fi

# Encoding: ffmpeg synthetic encode from test source
if command -v ffmpeg >/dev/null 2>&1; then
  encode_tool="ffmpeg_libx264"
  tmp="$(mktemp)"
  started="$(date +%s.%N)"
  if timeout "$((CPU_ENCODE_DURATION + 10))" ffmpeg -v error -f lavfi -i testsrc=size=1280x720:rate=30 \
      -t "$CPU_ENCODE_DURATION" -c:v libx264 -preset medium -f null - >"$tmp" 2>&1; then
    ended="$(date +%s.%N)"
    elapsed="$(awk -v s="$started" -v e="$ended" 'BEGIN {printf "%.3f", e-s}')"
    encode_status="ok"
    encode_score="$elapsed"
    notes+=("encoding=ffmpeg_libx264")
  elif ffmpeg -hide_banner -encoders 2>/dev/null | grep -q 'libx264'; then
    encode_status="failed"
    notes+=("encoding_ffmpeg_failed")
  else
    encode_tool="ffmpeg_mpeg4"
    started="$(date +%s.%N)"
    if timeout "$((CPU_ENCODE_DURATION + 10))" ffmpeg -v error -f lavfi -i testsrc=size=1280x720:rate=30 \
        -t "$CPU_ENCODE_DURATION" -c:v mpeg4 -q:v 5 -f null - >"$tmp" 2>&1; then
      ended="$(date +%s.%N)"
      elapsed="$(awk -v s="$started" -v e="$ended" 'BEGIN {printf "%.3f", e-s}')"
      encode_status="degraded"
      encode_score="$elapsed"
      notes+=("encoding=ffmpeg_mpeg4_fallback")
    else
      encode_status="failed"
      notes+=("encoding_ffmpeg_fallback_failed")
    fi
  fi
  rm -f "$tmp"
else
  notes+=("encoding_missing_ffmpeg")
fi

# Overall aggregation
if [[ "$baseline_status" == "failed" || "$compress_status" == "failed" || "$encode_status" == "failed" ]]; then
  status="failed"
elif [[ "$baseline_status" == "degraded" || "$compress_status" == "degraded" || "$encode_status" == "degraded" ]]; then
  status="degraded"
elif [[ "$baseline_status" == "skipped" && "$compress_status" == "skipped" && "$encode_status" == "skipped" ]]; then
  status="skipped"
fi

score="$baseline_score"
notes_str="$(IFS=';'; echo "${notes[*]}")"

cat > "$OUT_JSON" <<EOF
{
  "category": "cpu",
  "status": "$status",
  "benchmark": "$bench",
  "primary_metric": "baseline_score",
  "score": "${score}",
  "subtests": {
    "baseline": {
      "status": "$baseline_status",
      "tool": "$baseline_tool",
      "score": "${baseline_score}"
    },
    "compression": {
      "status": "$compress_status",
      "tool": "$compress_tool",
      "score": "${compress_score}"
    },
    "encoding": {
      "status": "$encode_status",
      "tool": "$encode_tool",
      "elapsed_sec": "${encode_score}"
    }
  },
  "notes": "$notes_str"
}
EOF

printf "category,status,benchmark,primary_metric,score,notes\n" > "$OUT_CSV"
printf "cpu,%s,%s,baseline_score,%s,%s\n" "$status" "$bench" "${score}" "${notes_str//,/;}" >> "$OUT_CSV"
