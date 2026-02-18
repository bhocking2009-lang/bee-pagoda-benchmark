#!/usr/bin/env bash
set -euo pipefail

OUT_JSON="$1"
OUT_CSV="$2"
DURATION="${GPU_GAME_DURATION:-60}"
WIDTH="${GPU_GAME_WIDTH:-1920}"
HEIGHT="${GPU_GAME_HEIGHT:-1080}"
TIMEOUT_SEC="${GPU_GAME_TIMEOUT_SEC:-0}"
if [[ "$TIMEOUT_SEC" -le 0 ]]; then
  TIMEOUT_SEC=$(( DURATION * 4 ))
  [[ "$TIMEOUT_SEC" -lt 120 ]] && TIMEOUT_SEC=120
fi

# auto|interactive|offscreen
MODE="${GPU_GAME_MODE:-auto}"
STRICT_GPU_GAME="${STRICT_GPU_GAME:-0}"

status="ok"
bench="none"
fps=""
frametime_ms=""
notes=""

# Runtime session diagnostics (helps explain headed/headless behavior)
DISPLAY_VAL="${DISPLAY:-unset}"
SESSION_TYPE_VAL="${XDG_SESSION_TYPE:-unset}"
GLMARK2_PATH="$(command -v glmark2 || true)"
if [[ -z "$GLMARK2_PATH" ]]; then GLMARK2_PATH="missing"; fi
echo "[GPU_GAME] diagnostics: DISPLAY=${DISPLAY_VAL} XDG_SESSION_TYPE=${SESSION_TYPE_VAL} glmark2=${GLMARK2_PATH}" >&2

have_display=0
if [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
  have_display=1
fi

if [[ "$MODE" == "auto" ]]; then
  if [[ $have_display -eq 1 ]]; then
    MODE="interactive"
  else
    MODE="offscreen"
  fi
fi

fail_or_degrade() {
  local msg="$1"
  if [[ "$STRICT_GPU_GAME" == "1" ]]; then
    status="failed"
  else
    status="degraded"
  fi
  notes="$msg"
}

run_glmark2_offscreen() {
  local tmp="$1"
  timeout "$TIMEOUT_SEC" glmark2 --off-screen --size "$WIDTH""x""$HEIGHT" >"$tmp" 2>&1
}

run_glmark2_interactive() {
  local tmp="$1"
  timeout "$TIMEOUT_SEC" glmark2 --size "$WIDTH""x""$HEIGHT" >"$tmp" 2>&1
}

run_vkmark_interactive() {
  local tmp="$1"
  timeout "$TIMEOUT_SEC" vkmark -s "$WIDTH""x""$HEIGHT" --benchmark >"$tmp" 2>&1
}

parse_vkmark() {
  local tmp="$1"
  local fps_val score_val
  fps_val="$(grep -iE 'fps|frames per second' "$tmp" | tail -n1 | grep -Eo '[0-9]+(\.[0-9]+)?' | tail -n1 || true)"
  score_val="$(grep -iE 'score' "$tmp" | tail -n1 | grep -Eo '[0-9]+(\.[0-9]+)?' | tail -n1 || true)"
  fps="${fps_val:-$score_val}"
}

parse_glmark2() {
  local tmp="$1"
  local score
  score="$(grep -iE '^glmark2 Score:' "$tmp" | awk '{print $3}' | tail -n1 || true)"
  fps="$score"
}

if [[ "$MODE" == "interactive" ]]; then
  tmp="$(mktemp)"
  if command -v vkmark >/dev/null 2>&1; then
    bench="vkmark"
    if run_vkmark_interactive "$tmp"; then
      parse_vkmark "$tmp"
      notes="mode=interactive;tool=vkmark;resolution=${WIDTH}x${HEIGHT};duration_hint=${DURATION}s"
    elif command -v glmark2 >/dev/null 2>&1 && run_glmark2_interactive "$tmp"; then
      bench="glmark2"
      parse_glmark2 "$tmp"
      notes="mode=interactive;vkmark_failed_then_glmark2_fallback;resolution=${WIDTH}x${HEIGHT}"
    elif command -v glmark2 >/dev/null 2>&1 && run_glmark2_offscreen "$tmp"; then
      bench="glmark2"
      parse_glmark2 "$tmp"
      notes="mode=interactive;vkmark_failed_then_glmark2_offscreen_fallback;resolution=${WIDTH}x${HEIGHT}"
    else
      fail_or_degrade "mode=interactive;vkmark/glmark2 failed (display/context/timeout)."
    fi
  elif command -v glmark2 >/dev/null 2>&1; then
    bench="glmark2"
    if run_glmark2_interactive "$tmp" || run_glmark2_offscreen "$tmp"; then
      parse_glmark2 "$tmp"
      notes="mode=interactive;tool=glmark2;resolution=${WIDTH}x${HEIGHT}"
    else
      fail_or_degrade "mode=interactive;glmark2 failed (display/context/timeout)."
    fi
  else
    status="skipped"
    notes="No game/graphics benchmark binary found (vkmark/glmark2)."
  fi
  rm -f "$tmp"

elif [[ "$MODE" == "offscreen" ]]; then
  tmp="$(mktemp)"
  if command -v glmark2 >/dev/null 2>&1; then
    bench="glmark2"
    if run_glmark2_offscreen "$tmp"; then
      parse_glmark2 "$tmp"
      notes="mode=offscreen;tool=glmark2;resolution=${WIDTH}x${HEIGHT}"
    else
      fail_or_degrade "mode=offscreen;glmark2 offscreen failed (context/timeout)."
    fi
  elif command -v vkmark >/dev/null 2>&1; then
    bench="vkmark"
    if run_vkmark_interactive "$tmp"; then
      parse_vkmark "$tmp"
      notes="mode=offscreen_fallback;tool=vkmark;resolution=${WIDTH}x${HEIGHT}"
    else
      fail_or_degrade "mode=offscreen;no glmark2 and vkmark failed."
    fi
  else
    status="skipped"
    notes="No game/graphics benchmark binary found (vkmark/glmark2)."
  fi
  rm -f "$tmp"
else
  status="failed"
  notes="Invalid GPU_GAME_MODE=${MODE}. Use auto|interactive|offscreen."
fi

if [[ -n "$fps" ]]; then
  frametime_ms="$(awk -v f="$fps" 'BEGIN{if(f>0) printf "%.3f", 1000/f; else print ""}')"
fi

# Always append session diagnostics into notes for post-run troubleshooting
if [[ -n "$notes" ]]; then
  notes="${notes};display=${DISPLAY_VAL};session=${SESSION_TYPE_VAL};glmark2=${GLMARK2_PATH}"
else
  notes="display=${DISPLAY_VAL};session=${SESSION_TYPE_VAL};glmark2=${GLMARK2_PATH}"
fi

cat > "$OUT_JSON" <<EOF
{
  "category": "gpu_game",
  "status": "$status",
  "benchmark": "$bench",
  "primary_metric": "fps",
  "fps": "${fps}",
  "frametime_ms": "${frametime_ms}",
  "notes": "$notes"
}
EOF

printf "category,status,benchmark,primary_metric,fps,frametime_ms,notes\n" > "$OUT_CSV"
printf "gpu_game,%s,%s,fps,%s,%s,%s\n" "$status" "$bench" "${fps}" "${frametime_ms}" "${notes//,/;}" >> "$OUT_CSV"
