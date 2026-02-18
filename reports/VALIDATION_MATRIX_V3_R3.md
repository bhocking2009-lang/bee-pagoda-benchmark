# Validation Matrix V3 Round 3

Date: 2026-02-17 20:50–20:51 EST

## Scope
- quick cpu: 3 runs
- balanced cpu: 1 run
- balanced full: 1 run
- verify CPU encoding subtest status
- verify suite exit code behavior

## Matrix Results

| Scenario | Command | Result | Exit Code | CPU Encoding Subtest | Evidence |
|---|---|---|---:|---|---|
| quick cpu run 1 | `./run_suite.sh quick cpu` | **FAIL** (cpu failed due compression) | 1 | **ok** | `reports/validation_v3_r3_artifacts/summaries/summary_quick_cpu_run1.md`, `reports/validation_v3_r3_artifacts/logs/quick_cpu_run1.log` |
| quick cpu run 2 | `./run_suite.sh quick cpu` | **FAIL** (cpu failed due compression) | 1 | **ok** | `reports/validation_v3_r3_artifacts/summaries/summary_quick_cpu_run2.md`, `reports/validation_v3_r3_artifacts/logs/quick_cpu_run2.log` |
| quick cpu run 3 | `./run_suite.sh quick cpu` | **FAIL** (cpu failed due compression) | 1 | **ok** | `reports/validation_v3_r3_artifacts/summaries/summary_quick_cpu_run3.md`, `reports/validation_v3_r3_artifacts/logs/quick_cpu_run3.log` |
| balanced cpu | `./run_suite.sh balanced cpu` | **FAIL** (cpu failed due compression) | 1 | **ok** | `reports/validation_v3_r3_artifacts/summaries/summary_balanced_cpu.md`, `reports/validation_v3_r3_artifacts/logs/balanced_cpu.log` |
| balanced full | `./run_suite.sh balanced` | **FAIL** (cpu failed; gpu_game degraded) | 1 | **ok** | `reports/validation_v3_r3_artifacts/summaries/summary_balanced_full.md`, `reports/validation_v3_r3_artifacts/logs/balanced_full.log` |

## Exit Code Behavior Validation

Expected semantics (from report footer):
- `0`: selected steps completed without `failed` status
- `1`: one or more selected benchmark steps failed
- `2`: usage/config error

Observed:
- All five runs exited with `1`.
- In each run, at least one benchmark step had `failed` status (cpu compression path), matching expected semantics.
- No usage/config error (`2`) observed.

Evidence: `reports/validation_v3_r3_artifacts/exit_codes.txt`

## CPU Encoding Subtest Validation

Observed in all five summaries:
- CPU key metrics include `encoding:ok` and `encoding=ffmpeg_libx264`.
- CPU failures are attributed to `compression:failed` (`compression_7z_failed`), not encoding.

Conclusion: **CPU encoding subtest is consistently OK in this validation matrix.**

## Artifact Index

- Exit codes: `reports/validation_v3_r3_artifacts/exit_codes.txt`
- Logs:
  - `reports/validation_v3_r3_artifacts/logs/quick_cpu_run1.log`
  - `reports/validation_v3_r3_artifacts/logs/quick_cpu_run2.log`
  - `reports/validation_v3_r3_artifacts/logs/quick_cpu_run3.log`
  - `reports/validation_v3_r3_artifacts/logs/balanced_cpu.log`
  - `reports/validation_v3_r3_artifacts/logs/balanced_full.log`
- Summary snapshots:
  - `reports/validation_v3_r3_artifacts/summaries/summary_quick_cpu_run1.md`
  - `reports/validation_v3_r3_artifacts/summaries/summary_quick_cpu_run2.md`
  - `reports/validation_v3_r3_artifacts/summaries/summary_quick_cpu_run3.md`
  - `reports/validation_v3_r3_artifacts/summaries/summary_balanced_cpu.md`
  - `reports/validation_v3_r3_artifacts/summaries/summary_balanced_full.md`
