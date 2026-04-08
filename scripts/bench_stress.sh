#!/usr/bin/env bash
# bench_stress.sh — System-Under-Load domain benchmark
# Runs a mixed CPU + memory + optional GPU stress period and measures
# throttling, thermal trend, and sustained performance delta.
set -euo pipefail

OUT_JSON="$1"
OUT_CSV="$2"

export LC_ALL=C

STRESS_DURATION="${STRESS_DURATION:-60}"
STRESS_TIMEOUT="${STRESS_TIMEOUT:-300}"
PYTHON_BIN="${BENCH_PYTHON:-python3}"

status="ok"
bench="system_under_load"
score=""
notes=()

throttling_detected="unknown"
thermal_trend="unknown"
sustained_delta=""

cpu_stress_status="skipped"
mem_stress_status="skipped"
thermal_samples=()
freq_start=""
freq_end=""

# ---- Helper: read current CPU frequency (MHz) ----
read_cpu_freq_mhz() {
  local freq=""
  # Try /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq (kHz -> MHz)
  if [[ -r /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq ]]; then
    local khz
    khz="$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || true)"
    if [[ -n "$khz" && "$khz" =~ ^[0-9]+$ ]]; then
      freq="$(awk -v k="$khz" 'BEGIN { printf "%.0f", k/1000 }')"
    fi
  fi
  echo "${freq:-}"
}

# ---- Helper: read thermal zone 0 temperature (°C) ----
read_thermal_celsius() {
  local temp=""
  for zone in /sys/class/thermal/thermal_zone*/temp; do
    [[ -r "$zone" ]] || continue
    local raw
    raw="$(cat "$zone" 2>/dev/null || true)"
    if [[ -n "$raw" && "$raw" =~ ^[0-9]+$ ]]; then
      temp="$(awk -v t="$raw" 'BEGIN { printf "%.1f", t/1000 }')"
      break
    fi
  done
  echo "${temp:-}"
}

# ---- Baseline CPU measurement (before stress) ----
baseline_eps=""
if command -v sysbench >/dev/null 2>&1; then
  baseline_tmp="$(mktemp)"
  if timeout 30 sysbench cpu --threads="$(nproc)" --time=10 run >"$baseline_tmp" 2>&1; then
    baseline_eps="$(grep -E 'events per second:' "$baseline_tmp" | awk '{print $4}' | tail -n1 || true)"
    notes+=("baseline_cpu_eps=${baseline_eps:-na}")
  fi
  rm -f "$baseline_tmp"
fi

freq_start="$(read_cpu_freq_mhz)"
temp_start="$(read_thermal_celsius)"
[[ -n "$temp_start" ]] && thermal_samples+=("$temp_start")

# ---- CPU stress ----
if command -v stress-ng >/dev/null 2>&1; then
  cpu_stress_status="running"
  stress_tmp="$(mktemp)"
  set +e
  timeout "$STRESS_TIMEOUT" stress-ng --cpu "$(nproc)" --cpu-method matrixprod \
    --timeout "${STRESS_DURATION}s" --metrics-brief >"$stress_tmp" 2>&1
  stress_rc=$?
  set -e
  if [[ $stress_rc -eq 0 || $stress_rc -eq 1 ]]; then
    cpu_stress_status="ok"
    bogo_ops="$(grep -E 'cpu\b' "$stress_tmp" | awk '{print $NF}' | head -n1 || true)"
    score="${bogo_ops:-}"
    notes+=("stress_ng_cpu_ok")
  else
    cpu_stress_status="failed"
    notes+=("stress_ng_cpu_failed:exit_${stress_rc}")
  fi
  rm -f "$stress_tmp"
elif command -v stress >/dev/null 2>&1; then
  cpu_stress_status="running"
  set +e
  timeout "$STRESS_TIMEOUT" stress --cpu "$(nproc)" --timeout "${STRESS_DURATION}s" >/dev/null 2>&1
  stress_rc=$?
  set -e
  if [[ $stress_rc -eq 0 || $stress_rc -eq 143 ]]; then
    cpu_stress_status="degraded"
    notes+=("stress_cpu_ok_no_metrics")
  else
    cpu_stress_status="failed"
    notes+=("stress_cpu_failed:exit_${stress_rc}")
  fi
else
  notes+=("stress_missing_stress_ng_stress")
fi

# ---- Thermal sample mid-stress ----
temp_mid="$(read_thermal_celsius)"
[[ -n "$temp_mid" ]] && thermal_samples+=("$temp_mid")

# ---- Memory stress ----
if command -v sysbench >/dev/null 2>&1; then
  mem_tmp="$(mktemp)"
  set +e
  timeout "$STRESS_TIMEOUT" sysbench memory --threads="$(nproc)" \
    --memory-total-size=100G --time="$STRESS_DURATION" run >"$mem_tmp" 2>&1
  mem_rc=$?
  set -e
  if [[ $mem_rc -eq 0 ]]; then
    mem_stress_status="ok"
    notes+=("sysbench_memory_stress_ok")
  else
    mem_stress_status="failed"
    notes+=("sysbench_memory_stress_failed:exit_${mem_rc}")
  fi
  rm -f "$mem_tmp"
else
  notes+=("mem_stress_missing_sysbench")
fi

# ---- Post-stress measurements ----
freq_end="$(read_cpu_freq_mhz)"
temp_end="$(read_thermal_celsius)"
[[ -n "$temp_end" ]] && thermal_samples+=("$temp_end")

# ---- Sustained performance delta (post vs baseline) ----
if [[ -n "$baseline_eps" ]] && command -v sysbench >/dev/null 2>&1; then
  post_tmp="$(mktemp)"
  if timeout 30 sysbench cpu --threads="$(nproc)" --time=10 run >"$post_tmp" 2>&1; then
    post_eps="$(grep -E 'events per second:' "$post_tmp" | awk '{print $4}' | tail -n1 || true)"
    if [[ -n "$post_eps" && -n "$baseline_eps" ]]; then
      sustained_delta="$(awk -v b="$baseline_eps" -v p="$post_eps" 'BEGIN {
        if (b > 0) printf "%.2f", (p - b) / b * 100
        else print "na"
      }')"
      notes+=("sustained_delta_pct=${sustained_delta}")
    fi
  fi
  rm -f "$post_tmp"
fi

# ---- Throttling detection ----
if [[ -n "$freq_start" && -n "$freq_end" ]]; then
  drop_pct="$(awk -v s="$freq_start" -v e="$freq_end" 'BEGIN {
    if (s > 0) printf "%.1f", (s - e) / s * 100
    else print "0"
  }')"
  # Consider >10% frequency drop as throttling
  throttling_detected="$(awk -v d="$drop_pct" 'BEGIN { print (d > 10) ? "yes" : "no" }')"
  notes+=("freq_drop_pct=${drop_pct}")
else
  notes+=("freq_measurement_unavailable")
fi

# ---- Thermal trend ----
if [[ ${#thermal_samples[@]} -ge 2 ]]; then
  t_first="${thermal_samples[0]}"
  t_last="${thermal_samples[${#thermal_samples[@]}-1]}"
  thermal_trend="$(awk -v f="$t_first" -v l="$t_last" 'BEGIN {
    diff = l - f
    if (diff > 5) print "rising"
    else if (diff < -5) print "falling"
    else print "stable"
  }')"
  notes+=("thermal_start=${t_first}C;thermal_end=${t_last}C")
fi

# ---- Overall status ----
if [[ "$cpu_stress_status" == "failed" && "$mem_stress_status" == "failed" ]]; then
  status="failed"
elif [[ "$cpu_stress_status" == "skipped" && "$mem_stress_status" == "skipped" ]]; then
  status="skipped"
elif [[ "$cpu_stress_status" == "failed" || "$mem_stress_status" == "failed" ]]; then
  status="degraded"
elif [[ "$cpu_stress_status" == "degraded" ]]; then
  status="degraded"
fi

notes_str="$(IFS=';'; echo "${notes[*]}")"

cat > "$OUT_JSON" <<EOF
{
  "category": "stress",
  "status": "$status",
  "benchmark": "$bench",
  "primary_metric": "bogo_ops_per_sec",
  "score": "${score}",
  "throttling_detected": "$throttling_detected",
  "thermal_trend": "$thermal_trend",
  "sustained_delta_pct": "${sustained_delta}",
  "subtests": {
    "cpu_stress": {
      "status": "$cpu_stress_status",
      "duration_sec": "$STRESS_DURATION"
    },
    "mem_stress": {
      "status": "$mem_stress_status",
      "duration_sec": "$STRESS_DURATION"
    }
  },
  "diagnostics": {
    "freq_start_mhz": "${freq_start}",
    "freq_end_mhz": "${freq_end}",
    "thermal_samples_c": [$(IFS=,; echo "${thermal_samples[*]:-}" | sed 's/,/, /g')],
    "baseline_cpu_eps": "${baseline_eps}"
  },
  "notes": "$notes_str"
}
EOF

printf "category,status,benchmark,primary_metric,score,throttling_detected,thermal_trend,sustained_delta_pct,notes\n" > "$OUT_CSV"
printf "stress,%s,%s,bogo_ops_per_sec,%s,%s,%s,%s,%s\n" \
  "$status" "$bench" "${score}" "$throttling_detected" "$thermal_trend" \
  "${sustained_delta}" "${notes_str//,/;}" >> "$OUT_CSV"
