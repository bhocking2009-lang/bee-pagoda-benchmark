# Linux Benchmark Tool — V2 Specification

Date: 2026-02-17
Status: Draft for implementation
Scope: Expand v1 into a modular, workload-representative Linux benchmarking platform (CLI-first, UI-ready later).

---

## 1) Goals

1. Provide meaningful benchmarks for real Linux users, not synthetic vanity numbers.
2. Cover full host performance: CPU, GPU, AI workloads, memory, storage, and system behavior under load.
3. Stay reproducible and scriptable on common Linux distros.
4. Degrade gracefully when tools are missing.
5. Produce machine-readable + human-readable outputs for comparisons over time.

---

## 2) Non-Goals (for v2)

- No GUI/launchpad implementation yet (design only).
- No cloud upload/telemetry backend.
- No vendor-locked benchmark dependencies as hard requirements.

---

## 3) Benchmark Domains (v2)

## 3.1 CPU Domain

### Required tests
- **CPU synthetic throughput**: `sysbench cpu`
- **Integer/crypto baseline**: `openssl speed`
- **Compression/decompression**: `7z b` (p7zip)
- **Compile workload**: controlled C/C++ build benchmark (small reproducible codebase)
- **Media encode**: `ffmpeg` x264/x265 timed encode

### Optional tests
- **CPU render**: Blender CLI benchmark (if blender installed)
- **CPU AI inference**: `llama.cpp` CPU-only tokens/sec

### Metrics
- throughput score(s)
- elapsed time
- per-thread scaling summary
- efficiency ratio (score/watt when power metrics available)

---

## 3.2 GPU Graphics / Gaming Domain

### Required tests
- `vkmark` (primary when display/Vulkan available)
- `glmark2 --off-screen` fallback

### Optional tests
- additional Vulkan/OpenGL microbench(s)
- game built-in benchmark adapters (plugin hooks)

### Metrics
- avg FPS
- derived frame-time ms (`1000/fps`)
- p95/p99 frame-time when tool supports detailed output
- resolution + API + driver metadata

---

## 3.3 GPU Compute / AI Domain

### Required tests
- `clpeak` (OpenCL capability/perf)
- `hashcat -b` fallback compute proxy

### AI-focused tests (new in v2)
- **llama.cpp CUDA/ROCm** tokens/sec benchmark (model configurable)
- **ONNX Runtime GPU** inference throughput benchmark (optional)
- **PyTorch CUDA microbench** (matmul/token throughput) when python stack exists

### Metrics
- tokens/sec or samples/sec
- latency per token/inference
- VRAM used
- backend (CUDA/ROCm/OpenCL)
- model/batch context

---

## 3.4 Memory Domain (new)

### Required tests
- `sysbench memory` bandwidth
- `tinymembench` (if available) for latency/bandwidth detail

### Metrics
- read/write MiB/s
- latency indicators
- NUMA/topology notes when detectable

---

## 3.5 Storage Domain (new)

### Required tests
- `fio` sequential read/write
- `fio` random 4k read/write (QD1 + higher queue depth)

### Safety rules
- default to test file in workspace, not raw block devices
- cap test file size/profile defaults to avoid accidental wear abuse

### Metrics
- IOPS
- MB/s
- p95/p99 latency
- test size and queue depth

---

## 3.6 System Under Load Domain (new)

### Required tests
- mixed load scenario (CPU + memory + disk + optional GPU)
- optional stress period with telemetry sampling

### Metrics
- throttling detected (yes/no)
- thermal trend
- sustained performance delta vs baseline

---

## 4) Standard Profiles

- **quick** (5–8 min): basic health + partial domains
- **balanced** (15–25 min): all core domains once
- **deep** (45–90 min): repeated runs + percentiles + stress segment
- **ai-focus** (new): CPU/GPU AI tests prioritized
- **gaming-focus** (new): graphics frametime-focused suite
- **storage-focus** (new): fio-heavy profile

Profiles are env files plus a JSON profile schema for future UI.

---

## 5) Plugin/Test Registry Architecture

Each benchmark is a module with:
- id, category, dependencies, fallback chain
- command builder
- parser
- normalization mapper
- error semantics

Run selections:
- by profile
- by category (`cpu,gpu,ai,memory,disk`)
- by explicit test IDs

Future launchpad can consume the same registry.

---

## 6) Output & Scoring Model

## 6.1 Output files per run
- `raw/*.json` per test
- `normalized/results.json`
- `report/summary.md`
- `report/summary.json`
- `report/summary.csv`
- `report/compare-prev.md` (when previous baseline exists)

## 6.2 Normalization
Store both:
1. **native tool metrics** (authoritative)
2. **normalized metrics** (common units + comparable fields)

## 6.3 Health bands
For each metric: `excellent/good/fair/poor/unknown` relative to local historical baseline (not internet leaderboard by default).

---

## 7) Reliability and Reproducibility Rules

- Pin command options and log exact command lines.
- Capture environment fingerprint:
  - kernel, distro, CPU model, RAM size/speed
  - GPU model/driver/API versions
  - power governor + thermal snapshot
- Warm-up pass for selected benchmarks where relevant.
- Retry policy for flaky tools (single retry max).
- Explicit status classes: `ok`, `skipped`, `failed`, `degraded`.

---

## 8) Dependency Strategy

## 8.1 Tiers
- **Tier A (recommended):** sysbench, openssl, glmark2, fio
- **Tier B (expanded):** vkmark, clpeak, hashcat, ffmpeg, p7zip
- **Tier C (advanced AI):** llama.cpp, onnxruntime bench, torch stack

Install script should detect distro family and install best-effort packages.

---

## 9) Security & Safety

- Never run destructive disk tests by default.
- Resource caps and timeout for each test.
- Clear warnings before long/deep stress tests.
- No outbound network needed for benchmark execution.

---

## 10) Exit Codes (v2)

- `0`: all required tests in selected scope succeeded (`ok` or allowed `degraded`)
- `1`: one or more required tests failed
- `2`: config/usage error
- `3`: dependency gate failed for required scope

---

## 11) Suggested Implementation Phases

## Phase 1 (core v2)
- Add memory + storage domains
- Add CPU workload expansion (7z/ffmpeg/compile)
- Add normalized result schema
- Add category selection CLI

## Phase 2 (AI + richer GPU)
- Add AI benchmark adapters (llama.cpp + optional ORT/PyTorch)
- Improve frametime percentile capture
- Add compare-to-previous report

## Phase 3 (prep for launchpad)
- Stabilize JSON profile schema
- Add progress event stream for future UI
- Add run manifest + resumable runs

---

## 12) Launchpad Readiness (Design Only, no implementation yet)

Planned future UX features:
- select tests by category/profile/advanced custom
- live progress + spinner + per-test status cards
- ETA and active command preview
- cancel/retry failed test module
- show quick scorecards and trend charts

CLI emits progress JSON lines now so future UI can subscribe without redesign.

---

## 13) Why this matters for Linux users

This spec avoids Windows-centric benchmark assumptions and focuses on practical Linux workloads: compile, encode, inference, graphics paths, storage latency, and sustained behavior under load. The result should feel useful for real machine decisions, not just synthetic bragging rights.
