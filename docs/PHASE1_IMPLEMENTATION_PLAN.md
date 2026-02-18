# Phase 1 Implementation Plan (v2)

Source of truth: `docs/BENCHMARK_V2_SPEC.md`

## Scope to deliver now
1. Add **memory** benchmark domain (`sysbench memory` + `tinymembench` fallback/details).
2. Add **storage** benchmark domain (`fio` safe file-based tests only).
3. Expand **CPU** domain with workload tests:
   - compression/decompression (`7z b`)
   - media encoding (`ffmpeg` timed encode)
   - keep baseline (`sysbench cpu` / `openssl speed` fallback)
4. Add CLI **category selection** while preserving profile-first usage.
5. Extend report generation for new domains + status handling.

## Design decisions
- Keep orchestrator as `run_suite.sh` with backward-compatible call:
  - existing: `./run_suite.sh balanced`
  - new: `./run_suite.sh balanced cpu,memory,disk`
  - optional long flag: `--categories cpu,gpu,ai,memory,disk`
- Maintain timestamped output dirs under `reports/run-<ts>-<profile>/`.
- Keep graceful dependency behavior:
  - missing tools => `skipped`
  - fallback-used where benchmark partially representative => `degraded`
  - command failures => `failed`
- Keep clear exit codes:
  - `0` success (no `failed` in selected scope)
  - `1` one or more selected tests failed
  - `2` usage/config error

## Implementation steps
1. Add `scripts/bench_memory.sh`.
2. Add `scripts/bench_storage.sh` (safe workspace fio file, capped size, cleanup).
3. Extend `scripts/bench_cpu.sh` to emit subtest metrics for baseline/compression/encoding.
4. Update `run_suite.sh` category parser + registry mapping (`cpu,gpu,ai,memory,disk`).
5. Extend `scripts/generate_report.py` to aggregate selected raw outputs and include richer CPU metrics/new domains.
6. Update `README.md` with new examples and category usage.
7. Validate with profile/category runs and verify artifacts/exit behavior.
8. Hardening fixes for any critical validation gaps.
