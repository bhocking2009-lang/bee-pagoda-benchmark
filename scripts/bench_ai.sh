#!/usr/bin/env bash
set -euo pipefail

OUT_JSON="$1"
OUT_CSV="$2"

PYTHON_BIN="${BENCH_PYTHON:-python3}"

TIMEOUT_SEC="${AI_TIMEOUT_SEC:-300}"
MODEL_PATH="${AI_MODEL_PATH:-}"
PROMPT_TOKENS="${AI_PROMPT_TOKENS:-512}"
GEN_TOKENS="${AI_GEN_TOKENS:-128}"
BATCH_SIZE="${AI_BATCH_SIZE:-512}"
CONTEXT_SIZE="${AI_CONTEXT_SIZE:-4096}"

AI_ENABLE_LLAMA="${AI_ENABLE_LLAMA:-1}"
AI_ENABLE_TORCH="${AI_ENABLE_TORCH:-1}"
AI_ENABLE_ONNXRUNTIME="${AI_ENABLE_ONNXRUNTIME:-1}"

AI_WEIGHT_LLAMA="${AI_WEIGHT_LLAMA:-1.0}"
AI_WEIGHT_TORCH="${AI_WEIGHT_TORCH:-1.0}"
AI_WEIGHT_ONNXRUNTIME="${AI_WEIGHT_ONNXRUNTIME:-1.0}"

AI_REF_LLAMA_TPS="${AI_REF_LLAMA_TPS:-100.0}"
AI_REF_TORCH_OPS="${AI_REF_TORCH_OPS:-2000000000.0}"
AI_REF_ONNXRUNTIME_OPS="${AI_REF_ONNXRUNTIME_OPS:-2000000000.0}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

find_llama_bench() {
  local c
  if [[ -n "${AI_LLAMA_BENCH_PATH:-}" && -x "${AI_LLAMA_BENCH_PATH}" ]]; then
    echo "${AI_LLAMA_BENCH_PATH}"
    return 0
  fi

  for c in llama-bench llama.cpp-bench; do
    if command -v "$c" >/dev/null 2>&1; then
      command -v "$c"
      return 0
    fi
  done

  local candidates=(
    "./llama.cpp/build/bin/llama-bench"
    "${ROOT_DIR}/llama.cpp/build/bin/llama-bench"
    "${ROOT_DIR}/../llama.cpp/build/bin/llama-bench"
    "${ROOT_DIR}/../llama.cpp/build/bin/llama.cpp-bench"
    "${ROOT_DIR}/llama.cpp/build/bin/llama.cpp-bench"
  )
  for c in "${candidates[@]}"; do
    if [[ -x "$c" ]]; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

run_llama_bench() {
  local llama_bin="$1"
  local tmp
  tmp="$(mktemp)"

  if [[ -z "$MODEL_PATH" ]]; then
    "$PYTHON_BIN" - <<'PY'
import json
print(json.dumps({
  "backend": "llama.cpp",
  "status": "skipped",
  "benchmark": "llama.cpp",
  "primary_metric": "tokens_per_sec",
  "data_source": "real_model",
  "score": None,
  "prompt_tps": None,
  "eval_tps": None,
  "model": None,
  "context_size": None,
  "batch_size": None,
  "notes": "llama.cpp benchmark available but AI_MODEL_PATH is not set"
}))
PY
    rm -f "$tmp"
    return 0
  fi

  if [[ ! -f "$MODEL_PATH" ]]; then
    "$PYTHON_BIN" - "$MODEL_PATH" <<'PY'
import json, sys
print(json.dumps({
  "backend": "llama.cpp",
  "status": "skipped",
  "benchmark": "llama.cpp",
  "primary_metric": "tokens_per_sec",
  "data_source": "real_model",
  "score": None,
  "prompt_tps": None,
  "eval_tps": None,
  "model": sys.argv[1],
  "context_size": None,
  "batch_size": None,
  "notes": f"AI_MODEL_PATH does not exist: {sys.argv[1]}"
}))
PY
    rm -f "$tmp"
    return 0
  fi

  if timeout "$TIMEOUT_SEC" "$llama_bin" -m "$MODEL_PATH" -p "$PROMPT_TOKENS" -n "$GEN_TOKENS" -b "$BATCH_SIZE" -c "$CONTEXT_SIZE" >"$tmp" 2>&1; then
    "$PYTHON_BIN" - "$tmp" "$MODEL_PATH" "$CONTEXT_SIZE" "$BATCH_SIZE" <<'PY'
import json
import re
import sys

path, model_path, context_size, batch_size = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
text = open(path, "r", errors="ignore").read()

prompt = None
eval_t = None
model = model_path
ctx = context_size

for ln in text.splitlines():
    l = ln.strip()
    if model == model_path and ("model" in l.lower() or "filename" in l.lower()):
        m = re.search(r"(?:model|filename)\s*[:=]\s*(.+)", l, re.I)
        if m:
            model = m.group(1).strip().strip('"')
    m = re.search(r"(?:ctx(?:_| )?size|context(?:_| )?size|n_ctx)\s*[:=]\s*(\d+)", l, re.I)
    if m:
        ctx = m.group(1)
    if prompt is None:
        m = re.search(r"(?:pp\d+|prompt(?:\s+eval)?)\D+([0-9]+(?:\.[0-9]+)?)\s*(?:tok/s|t/s)", l, re.I)
        if m:
            prompt = float(m.group(1))
    if eval_t is None:
        m = re.search(r"(?:tg\d+|eval|decode|generation)\D+([0-9]+(?:\.[0-9]+)?)\s*(?:tok/s|t/s)", l, re.I)
        if m:
            eval_t = float(m.group(1))

score = eval_t if eval_t is not None else prompt
status = "ok" if score is not None else "degraded"
notes = "llama.cpp benchmark complete" if score is not None else "llama.cpp ran but token throughput could not be parsed"

print(json.dumps({
  "backend": "llama.cpp",
  "status": status,
  "benchmark": "llama.cpp",
  "primary_metric": "tokens_per_sec",
  "data_source": "real_model",
  "score": score,
  "prompt_tps": prompt,
  "eval_tps": eval_t,
  "model": model,
  "context_size": ctx,
  "batch_size": batch_size,
  "notes": notes
}))
PY
  else
    "$PYTHON_BIN" - <<'PY'
import json
print(json.dumps({
  "backend": "llama.cpp",
  "status": "failed",
  "benchmark": "llama.cpp",
  "primary_metric": "tokens_per_sec",
  "data_source": "real_model",
  "score": None,
  "prompt_tps": None,
  "eval_tps": None,
  "model": None,
  "context_size": None,
  "batch_size": None,
  "notes": "llama.cpp benchmark execution failed or timed out"
}))
PY
  fi

  rm -f "$tmp"
}

run_python_backend() {
  local backend="$1"
  "$PYTHON_BIN" - "$backend" "$BATCH_SIZE" "$CONTEXT_SIZE" <<'PY'
import importlib.util
import json
import math
import statistics
import sys
import time

backend = sys.argv[1]
batch_size = max(1, int(sys.argv[2]))
context_size = max(1, int(sys.argv[3]))


def have(module: str) -> bool:
    return importlib.util.find_spec(module) is not None

if backend == "onnxruntime":
    if not have("onnxruntime"):
        print(json.dumps({
            "backend": "onnxruntime",
            "status": "skipped",
            "benchmark": "onnxruntime_microbench",
            "primary_metric": "ops_per_sec",
            "data_source": "synthetic_proxy",
            "score": None,
            "prompt_tps": None,
            "eval_tps": None,
            "model": "synthetic-matmul",
            "context_size": context_size,
            "batch_size": batch_size,
            "notes": "onnxruntime package not installed"
        }))
        sys.exit(0)
    try:
        import onnxruntime  # noqa:F401
        import numpy as np

        n = min(2048, max(256, int(math.sqrt(batch_size * 1024))))
        a = np.random.rand(n, n).astype("float32")
        b = np.random.rand(n, n).astype("float32")
        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            _ = a @ b
            times.append(time.perf_counter() - t0)
        med = max(1e-9, statistics.median(times))
        ops = (2 * (n ** 3)) / med
        tps_proxy = ops / max(1, context_size)
        print(json.dumps({
            "backend": "onnxruntime",
            "status": "degraded",
            "benchmark": "onnxruntime_microbench",
            "primary_metric": "ops_per_sec",
            "data_source": "synthetic_proxy",
            "score": ops,
            "prompt_tps": tps_proxy,
            "eval_tps": tps_proxy,
            "model": "synthetic-matmul",
            "context_size": context_size,
            "batch_size": batch_size,
            "notes": "ONNX Runtime microbench proxy (CPU matmul)"
        }))
    except Exception as e:
        print(json.dumps({
            "backend": "onnxruntime",
            "status": "failed",
            "benchmark": "onnxruntime_microbench",
            "primary_metric": "ops_per_sec",
            "data_source": "synthetic_proxy",
            "score": None,
            "prompt_tps": None,
            "eval_tps": None,
            "model": "synthetic-matmul",
            "context_size": context_size,
            "batch_size": batch_size,
            "notes": f"onnxruntime runtime error: {e}"
        }))
elif backend == "torch":
    if not have("torch"):
        print(json.dumps({
            "backend": "torch",
            "status": "skipped",
            "benchmark": "torch_microbench",
            "primary_metric": "ops_per_sec",
            "data_source": "synthetic_proxy",
            "score": None,
            "prompt_tps": None,
            "eval_tps": None,
            "model": "synthetic-matmul",
            "context_size": context_size,
            "batch_size": batch_size,
            "notes": "torch package not installed"
        }))
        sys.exit(0)
    try:
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        n = min(2048, max(256, int(math.sqrt(batch_size * 1024))))
        a = torch.rand((n, n), device=device)
        b = torch.rand((n, n), device=device)
        if device == "cuda":
            torch.cuda.synchronize()
        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            _ = a @ b
            if device == "cuda":
                torch.cuda.synchronize()
            times.append(time.perf_counter() - t0)
        med = max(1e-9, statistics.median(times))
        ops = (2 * (n ** 3)) / med
        tps_proxy = ops / max(1, context_size)
        print(json.dumps({
            "backend": "torch",
            "status": "degraded",
            "benchmark": "torch_microbench",
            "primary_metric": "ops_per_sec",
            "data_source": "synthetic_proxy",
            "score": ops,
            "prompt_tps": tps_proxy,
            "eval_tps": tps_proxy,
            "model": f"synthetic-matmul-{device}",
            "context_size": context_size,
            "batch_size": batch_size,
            "notes": f"PyTorch microbench proxy ({device} matmul)"
        }))
    except Exception as e:
        print(json.dumps({
            "backend": "torch",
            "status": "failed",
            "benchmark": "torch_microbench",
            "primary_metric": "ops_per_sec",
            "data_source": "synthetic_proxy",
            "score": None,
            "prompt_tps": None,
            "eval_tps": None,
            "model": "synthetic-matmul",
            "context_size": context_size,
            "batch_size": batch_size,
            "notes": f"torch runtime error: {e}"
        }))
else:
    print(json.dumps({"backend": backend, "status": "skipped", "notes": "unsupported backend"}))
PY
}

RESULTS_FILE="$(mktemp)"
: > "$RESULTS_FILE"

append_result() {
  local payload="$1"
  printf '%s\n' "$payload" >> "$RESULTS_FILE"
}

if [[ "$AI_ENABLE_LLAMA" == "1" ]]; then
  if llama_bin="$(find_llama_bench)"; then
    append_result "$(run_llama_bench "$llama_bin")"
  else
    append_result "$("$PYTHON_BIN" - <<'PY'
import json
print(json.dumps({
  "backend": "llama.cpp",
  "status": "skipped",
  "benchmark": "llama.cpp",
  "primary_metric": "tokens_per_sec",
  "data_source": "real_model",
  "score": None,
  "prompt_tps": None,
  "eval_tps": None,
  "model": None,
  "context_size": None,
  "batch_size": None,
  "notes": "llama-bench not found in PATH or ./llama.cpp/build/bin"
}))
PY
)"
  fi
else
  append_result "$("$PYTHON_BIN" - <<'PY'
import json
print(json.dumps({
  "backend": "llama.cpp",
  "status": "skipped",
  "benchmark": "llama.cpp",
  "primary_metric": "tokens_per_sec",
  "data_source": "real_model",
  "disabled": True,
  "disabled_by": "AI_ENABLE_LLAMA",
  "score": None,
  "prompt_tps": None,
  "eval_tps": None,
  "model": None,
  "context_size": None,
  "batch_size": None,
  "notes": "disabled by AI_ENABLE_LLAMA=0"
}))
PY
)"
fi

if [[ "$AI_ENABLE_ONNXRUNTIME" == "1" ]]; then
  append_result "$(run_python_backend onnxruntime)"
else
  append_result "$("$PYTHON_BIN" - <<'PY'
import json
print(json.dumps({
  "backend": "onnxruntime",
  "status": "skipped",
  "benchmark": "onnxruntime_microbench",
  "primary_metric": "ops_per_sec",
  "data_source": "synthetic_proxy",
  "disabled": True,
  "disabled_by": "AI_ENABLE_ONNXRUNTIME",
  "score": None,
  "prompt_tps": None,
  "eval_tps": None,
  "model": None,
  "context_size": None,
  "batch_size": None,
  "notes": "disabled by AI_ENABLE_ONNXRUNTIME=0"
}))
PY
)"
fi

if [[ "$AI_ENABLE_TORCH" == "1" ]]; then
  append_result "$(run_python_backend torch)"
else
  append_result "$("$PYTHON_BIN" - <<'PY'
import json
print(json.dumps({
  "backend": "torch",
  "status": "skipped",
  "benchmark": "torch_microbench",
  "primary_metric": "ops_per_sec",
  "data_source": "synthetic_proxy",
  "disabled": True,
  "disabled_by": "AI_ENABLE_TORCH",
  "score": None,
  "prompt_tps": None,
  "eval_tps": None,
  "model": None,
  "context_size": None,
  "batch_size": None,
  "notes": "disabled by AI_ENABLE_TORCH=0"
}))
PY
)"
fi

"$PYTHON_BIN" - "$RESULTS_FILE" "$OUT_JSON" "$OUT_CSV" \
  "$AI_WEIGHT_LLAMA" "$AI_WEIGHT_ONNXRUNTIME" "$AI_WEIGHT_TORCH" \
  "$AI_REF_LLAMA_TPS" "$AI_REF_ONNXRUNTIME_OPS" "$AI_REF_TORCH_OPS" <<'PY'
import csv
import json
import math
import sys

results_file, out_json, out_csv = sys.argv[1], sys.argv[2], sys.argv[3]
weight_llama, weight_onnx, weight_torch = map(float, sys.argv[4:7])
ref_llama, ref_onnx, ref_torch = map(float, sys.argv[7:10])

backend_results = [json.loads(line) for line in open(results_file) if line.strip()]

weights = {
    "llama.cpp": weight_llama,
    "onnxruntime": weight_onnx,
    "torch": weight_torch,
}
refs = {
    "llama.cpp": ref_llama,
    "onnxruntime": ref_onnx,
    "torch": ref_torch,
}

status_counts = {"ok": 0, "degraded": 0, "skipped": 0, "failed": 0}
for r in backend_results:
    s = r.get("status", "skipped")
    if s in status_counts:
        status_counts[s] += 1

real_backends = [r for r in backend_results if r.get("data_source") == "real_model"]
synthetic_backends = [r for r in backend_results if r.get("data_source") == "synthetic_proxy"]

real_ok = [r for r in real_backends if r.get("status") == "ok"]
real_ran = [r for r in real_backends if r.get("status") in ("ok", "degraded", "failed")]
real_failed = [r for r in real_backends if r.get("status") == "failed"]
synthetic_ok = [r for r in synthetic_backends if r.get("status") in ("ok", "degraded")]

if real_ok and not real_failed:
    overall = "ok"
elif real_ran or synthetic_ok or real_failed:
    overall = "degraded"
else:
    overall = "skipped"

normalized = {}
weighted_sum = 0.0
weight_sum = 0.0

for r in real_ok:
    b = r.get("backend")
    score = r.get("score")
    if score in (None, ""):
        continue
    try:
        score = float(score)
    except Exception:
        continue
    w = max(0.0, float(weights.get(b, 0.0)))
    ref = max(1e-9, float(refs.get(b, 1.0)))
    norm = min(1.0, score / ref)
    normalized[b] = norm
    weighted_sum += norm * w
    weight_sum += w

composite = (weighted_sum / weight_sum) if weight_sum > 0 else None
credible_ai_mode = len(real_ok) > 0

primary = next((r for r in real_ok if r.get("backend") == "llama.cpp"), None)
if not primary:
    primary = next((r for r in real_ok), None)
if not primary:
    primary = next((r for r in backend_results if r.get("backend") == "llama.cpp"), backend_results[0] if backend_results else {})

summary = {
    "category": "ai",
    "status": overall,
    "benchmark": "multi_backend_ai",
    "backend": "multi",
    "primary_metric": "composite_normalized",
    "score": composite,
    "prompt_tps": primary.get("prompt_tps"),
    "eval_tps": primary.get("eval_tps"),
    "model": primary.get("model"),
    "context_size": primary.get("context_size"),
    "batch_size": primary.get("batch_size"),
    "data_source": "real_model" if credible_ai_mode else "synthetic_proxy",
    "credible_ai_mode": credible_ai_mode,
    "notes": "real-model-first: llama.cpp GGUF run required for credible AI mode; synthetic backends are optional proxies",
    "backend_results": backend_results,
    "real_model": {
        "ok": len(real_ok),
        "ran": len(real_ran),
        "failed": len(real_failed),
    },
    "synthetic_proxy": {
        "ok_or_degraded": len(synthetic_ok),
        "total": len(synthetic_backends),
    },
    "composite": {
        "score": composite,
        "display": composite if composite is not None else "N/A",
        "normalized_by_backend": normalized,
        "weights": weights,
        "references": refs,
        "formula": "composite = sum(weight_b * min(1.0, score_b/reference_b)) / sum(weights for successful real_model backends only)",
    },
}

with open(out_json, "w") as f:
    json.dump(summary, f, indent=2)

with open(out_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["category","status","benchmark","backend","primary_metric","score","prompt_tps","eval_tps","model","context_size","batch_size","notes"])
    w.writerow([
        summary.get("category"),
        summary.get("status"),
        summary.get("benchmark"),
        summary.get("backend"),
        summary.get("primary_metric"),
        "" if summary.get("score") is None else summary.get("score"),
        "" if summary.get("prompt_tps") is None else summary.get("prompt_tps"),
        "" if summary.get("eval_tps") is None else summary.get("eval_tps"),
        summary.get("model") or "",
        summary.get("context_size") or "",
        summary.get("batch_size") or "",
        summary.get("notes") or "",
    ])
PY

rm -f "$RESULTS_FILE"
