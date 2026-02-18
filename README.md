# Project Linux Benchmark Tool

Automated Linux host benchmark suite for:
- CPU throughput + workload tests
- GPU compute throughput
- AI inference throughput (multi-backend: llama.cpp bench + ONNX Runtime microbench + PyTorch microbench)
- In-game / graphics workload performance (FPS + derived frame-time)
- Memory bandwidth/latency-oriented tests
- Storage performance with safe file-based fio runs

## Deliverables Included

1. Project folder with scripts ✅
2. One-command runner ✅ (`./run_suite.sh`)
3. Dependency/install script ✅ (`scripts/install_dependencies.sh`)
4. Benchmark config profiles ✅ (`profiles/*.env`)
5. Report generator (Markdown + JSON + CSV) ✅
6. Sample output (if runnable on host) ✅ under `sample-output/` and `reports/`
7. README with usage and troubleshooting ✅

## Layout

- `run_suite.sh` - main orchestrator
- `scripts/install_dependencies.sh` - installs optional dependencies
- `scripts/bench_cpu.sh` - CPU benchmark suite (baseline + compression + encoding)
- `scripts/bench_gpu_compute.sh` - GPU compute wrapper (clpeak, fallback hashcat)
- `scripts/bench_gpu_game.sh` - session-aware graphics/game benchmark wrapper (`GPU_GAME_MODE=auto|interactive|offscreen`)
- `scripts/bench_ai.sh` - AI multi-backend benchmark adapter (llama.cpp + ONNX Runtime + PyTorch)
- `scripts/preflight_check.sh` - preflight dependency scanner (standalone + suite-integrated)
- `scripts/bench_memory.sh` - memory tests (sysbench memory + tinymembench)
- `scripts/bench_storage.sh` - storage tests (fio sequential + random 4k, safe file default)
- `scripts/generate_report.py` - emits report files + preflight section
- `profiles/quick.env` - short run
- `profiles/balanced.env` - default
- `profiles/deep.env` - longer, repeated runs
- `reports/` - timestamped run artifacts

## One-Command Full Suite

```bash
cd /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool
./run_suite.sh balanced
```

`run_suite.sh` auto-selects Python in this order for consistency across preflight/AI/reporting:
1. `--python /path/to/python` (explicit override)
2. active shell virtualenv (`$VIRTUAL_ENV/bin/python`)
3. local project venv (`./.venv/bin/python`, then `./.venv312/bin/python`)
4. system `python3`

By default, suite start runs a preflight dependency scan before benchmarks.

```bash
# Skip preflight only when needed
./run_suite.sh quick ai --skip-preflight
```

## Category Selection (Phase 1 v2)

You can now scope by categories while preserving profile behavior.

```bash
# profile + comma-separated positional categories
./run_suite.sh quick cpu,memory,disk

# profile + explicit flag
./run_suite.sh balanced --categories cpu,gpu,ai,memory,disk

# force a specific interpreter (useful in CI)
./run_suite.sh balanced --categories ai --python ./.venv/bin/python

# gpu expands to gpu_compute + gpu_game
# ai runs dedicated AI benchmarks (llama.cpp adapter or fallback microbench)
```

## AI Benchmarking (Phase 2.5)

Exact commands:

```bash
# Run only AI category with quick profile defaults
./run_suite.sh quick ai

# Run AI with llama.cpp model configured + explicit backend controls
AI_MODEL_PATH=/absolute/path/to/model.gguf \
AI_ENABLE_LLAMA=1 AI_ENABLE_TORCH=1 AI_ENABLE_ONNXRUNTIME=1 \
AI_PROMPT_TOKENS=512 AI_GEN_TOKENS=128 AI_BATCH_SIZE=512 AI_CONTEXT_SIZE=4096 \
./run_suite.sh balanced --categories ai
```

AI profile knobs (in `profiles/*.env`):
- `AI_MODEL_PATH` - `.gguf` model path for llama.cpp benchmark
- `AI_LLAMA_BENCH_PATH` - optional explicit path to `llama-bench` binary
- `AI_PROMPT_TOKENS` - prompt-token load for benchmark
- `AI_GEN_TOKENS` - generation/eval token count
- `AI_BATCH_SIZE` - batch size for llama.cpp and microbench backends
- `AI_CONTEXT_SIZE` - context length target
- `AI_TIMEOUT_SEC` - benchmark timeout
- `AI_ENABLE_LLAMA`, `AI_ENABLE_TORCH`, `AI_ENABLE_ONNXRUNTIME` - backend enable/disable toggles
- `AI_WEIGHT_LLAMA`, `AI_WEIGHT_TORCH`, `AI_WEIGHT_ONNXRUNTIME` - composite weighting knobs
- `AI_REF_LLAMA_TPS`, `AI_REF_TORCH_OPS`, `AI_REF_ONNXRUNTIME_OPS` - normalization references for transparent composite score

AI backend modes:
- **llama.cpp mode**: requires `llama-bench` and `AI_MODEL_PATH`; yields native token throughput (`data_source=real_model`).
- **microbench mode** (torch/onnxruntime): synthetic matmul throughput proxies (`data_source=synthetic_proxy`).
- **mixed mode** (default): runs all enabled backends independently and reports each result plus composite helper score.

Composite formula (also emitted in report/JSON notes):
- `composite = sum(weight_b * min(1.0, score_b/reference_b)) / sum(weights for backends with numeric score)`
- Native backend metrics remain primary truth (`backend_results[]` in raw AI JSON).
- AI result entries include `data_source`: `real_model` (llama.cpp with GGUF) vs `synthetic_proxy` (microbench backends).

## Install Dependencies (Optional but Recommended)

```bash
./scripts/install_dependencies.sh
```

AI dependency notes:
- Installer provisions a local `.venv` and attempts `pip install onnxruntime torch` (best-effort).
- Preferred llama backend: `llama-bench` in `PATH` or `./llama.cpp/build/bin/llama-bench` plus local GGUF model (`AI_MODEL_PATH`).
- Multi-backend behavior: each backend runs independently; missing backend is marked `skipped` (or `optional-missing` in preflight) and does not fail whole AI step.

## Preflight Checks

Run standalone:

```bash
./scripts/preflight_check.sh
# or explicit outputs
./scripts/preflight_check.sh ./reports/preflight.json ./reports/preflight.csv
```

Detected dependencies include:
- python3, pip, torch, onnxruntime, llama-bench
- nvcc (CUDA toolkit), nvidia-smi (driver/runtime)
- clpeak, vkmark, glmark2, fio, sysbench, ffmpeg, 7z, tinymembench, hashcat

Status classes:
- `present`
- `missing`
- `version-mismatch`
- `optional-missing`

## Output Artifacts

For each run, a folder is created under `reports/run-<timestamp>-<profile>/`:

- `raw/preflight.json`, `raw/preflight.csv`
- `raw/cpu.json`, `raw/gpu_compute.json`, `raw/gpu_game.json`, `raw/ai.json`, `raw/memory.json`, `raw/disk.json`
- `report/summary.md`
- `report/summary.json`
- `report/summary.csv`

## Exit Codes

- `0`: selected scope completed with no `failed` status
- `1`: at least one selected benchmark step failed
- `2`: usage or profile/config error

## Fallback / Status Strategy

- CPU baseline: `sysbench` → fallback `openssl speed`
- CPU workload: `7z b` + `ffmpeg` encode (best-effort fallback codec)
- GPU compute: `clpeak` → fallback `hashcat -b`
- AI: runs all enabled backends independently in one invocation:
  - `llama-bench` (llama.cpp) when binary + model are available
  - ONNX Runtime microbench when Python package is available
  - PyTorch microbench when Python package is available
  - Missing backend => backend-level `skipped`; AI category becomes `ok`/`degraded`/`skipped`/`failed` from aggregate backend statuses
- GPU game/graphics: session-aware mode
  - `offscreen` (default profiles): run in-process without pop-up windows via `glmark2 --off-screen`
  - `interactive`: prefer `vkmark`/interactive contexts, fallback to glmark2
  - `auto`: choose based on display/session availability
- Memory: `sysbench memory` + `tinymembench` when available
- Storage: `fio` file-based tests only (workspace run dir)

Statuses in reports:
- `ok` - benchmark ran successfully with primary path
- `degraded` - fallback used / partial representative coverage (still usable data)
- `skipped` - dependency missing or intentionally unavailable
- `failed` - benchmark attempted but failed

Strictness semantics:
- Default behavior favors **degraded over failed** when an optional backend/tool is unavailable.
- `STRICT_GPU_GAME=1` upgrades GPU game benchmark errors from degraded/skipped-style tolerance to hard failure.
- Suite exit code remains `1` only when a selected category ends in `failed`.

## Safety & Idempotency

- Storage tests use a generated file inside the run workspace (never raw block devices by default).
- Safe to rerun; every execution writes a fresh timestamped report directory.
- Scripts avoid mutating existing run output.

## Troubleshooting

- **Graphics context issues**: profiles default to `GPU_GAME_MODE=offscreen` to avoid display coupling.
  - For desktop windowed runs, set `GPU_GAME_MODE=interactive`.
  - To avoid failing full runs on graphics-context problems, keep `STRICT_GPU_GAME=0` (default).
- **No benchmark tools installed**: run `./scripts/install_dependencies.sh` or install manually.
- **Permission issues with package manager**: rerun install script with a sudo-capable user.
- **Missing Python**: install `python3`; report generator requires Python 3.
