#!/usr/bin/env bash
set -euo pipefail

OUT_JSON="$1"
OUT_CSV="$2"

DURATION="${CPU_DURATION:-60}"
THREADS="${CPU_THREADS:-0}"
[[ "$THREADS" == "0" ]] && THREADS="$(nproc)"

CPU_COMPRESS_DURATION="${CPU_COMPRESS_DURATION:-20}"
CPU_ENCODE_DURATION="${CPU_ENCODE_DURATION:-20}"

PYTHON_BIN="${BENCH_PYTHON:-python3}"

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

ffmpeg_bin=""
ffmpeg_version=""
encode_command=""
encode_error_tail=""
encode_error_code=""
encode_error_reason=""
encode_timeout_used=""
encode_output_target="${CPU_FFMPEG_NULL_TARGET:-/dev/null}"

resolve_ffmpeg_bin() {
  local explicit="${CPU_FFMPEG_BIN:-${FFMPEG_BIN:-}}"
  if [[ -n "$explicit" ]]; then
    if [[ -x "$explicit" ]]; then
      echo "$explicit"
      return 0
    fi
    return 1
  fi

  if command -v ffmpeg >/dev/null 2>&1; then
    command -v ffmpeg
    return 0
  fi

  return 1
}

capture_ffmpeg_version() {
  local bin="$1"
  "$bin" -version 2>/dev/null | head -n1 | sed -E 's/[[:space:]]+/ /g' || true
}

run_with_optional_timeout() {
  local timeout_sec="$1"
  shift

  if command -v timeout >/dev/null 2>&1; then
    encode_timeout_used="timeout"
    timeout --foreground "$timeout_sec" "$@"
    return $?
  fi

  encode_timeout_used="none"
  "$@"
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
  if timeout "$CPU_COMPRESS_DURATION" 7z b -mmt="$THREADS" >"$tmp" 2>&1; then
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
if ffmpeg_bin="$(resolve_ffmpeg_bin)"; then
  ffmpeg_version="$(capture_ffmpeg_version "$ffmpeg_bin")"
  timeout_sec="$((CPU_ENCODE_DURATION + 20))"

  run_encode_once() {
    local tmp_file="$1"
    shift

    local started ended rc
    started="$(date +%s.%N)"
    set +e
    run_with_optional_timeout "$timeout_sec" "$ffmpeg_bin" -v error -nostdin -hide_banner -nostats \
      -f lavfi -i testsrc=size=1280x720:rate=30 -t "$CPU_ENCODE_DURATION" "$@" -f null "$encode_output_target" >"$tmp_file" 2>&1
    rc=$?
    set -e

    if [[ $rc -eq 0 ]]; then
      ended="$(date +%s.%N)"
      encode_score="$(awk -v s="$started" -v e="$ended" 'BEGIN {printf "%.3f", e-s}')"
      return 0
    fi

    encode_error_code="$rc"
    if [[ $rc -eq 124 || $rc -eq 137 ]]; then
      encode_error_reason="timeout"
    else
      encode_error_reason="exit_${rc}"
    fi
    return 1
  }

  tmp="$(mktemp)"
  encode_command="$ffmpeg_bin -v error -nostdin -hide_banner -nostats -f lavfi -i testsrc=size=1280x720:rate=30 -t $CPU_ENCODE_DURATION -c:v libx264 -preset medium -f null $encode_output_target"
  if run_encode_once "$tmp" -c:v libx264 -preset medium; then
    encode_tool="ffmpeg_libx264"
    encode_status="ok"
    notes+=("encoding=ffmpeg_libx264")
  else
    encode_command="$ffmpeg_bin -v error -nostdin -hide_banner -nostats -f lavfi -i testsrc=size=1280x720:rate=30 -t $CPU_ENCODE_DURATION -c:v mpeg4 -q:v 5 -pix_fmt yuv420p -f null $encode_output_target"
    if run_encode_once "$tmp" -c:v mpeg4 -q:v 5 -pix_fmt yuv420p; then
      encode_tool="ffmpeg_mpeg4"
      encode_status="degraded"
      notes+=("encoding=ffmpeg_mpeg4_fallback")
    else
      encode_tool="ffmpeg_mpeg4"
      encode_status="failed"
      encode_error_tail="$(tail -n 40 "$tmp" | tr '\n' '|' | tr '"' "'" | tr ';' ',' | sed -E 's/\|+$//' || true)"
      if [[ -z "$encode_error_tail" ]]; then
        encode_error_tail="no_stderr_output"
      fi
      notes+=("encoding_ffmpeg_fallback_failed:${encode_error_reason}:${encode_error_tail}")
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
  "diagnostics": {
    "python_interpreter": "$PYTHON_BIN",
    "cpu_threads": "$THREADS",
    "ffmpeg": {
      "path": "${ffmpeg_bin}",
      "version": "${ffmpeg_version}",
      "command": "${encode_command}",
      "output_target": "${encode_output_target}",
      "timeout_wrapper": "${encode_timeout_used}",
      "error_code": "${encode_error_code}",
      "error_reason": "${encode_error_reason}",
      "error_tail": "${encode_error_tail}"
    }
  },
  "notes": "$notes_str"
}
EOF

printf "category,status,benchmark,primary_metric,score,notes\n" > "$OUT_CSV"
printf "cpu,%s,%s,baseline_score,%s,%s\n" "$status" "$bench" "${score}" "${notes_str//,/;}" >> "$OUT_CSV"
