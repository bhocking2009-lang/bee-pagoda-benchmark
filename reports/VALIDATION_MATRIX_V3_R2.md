# Validation Matrix v3 Round 2 (Validator)

Date: 2026-02-17 (EST)
Project: `/home/openclaw/.openclaw/workspace/project-linux-benchmark-tool`
Artifacts: `reports/validation_v3_r2_artifacts/`

## Scope Executed
- quick `gpu,memory,disk` with preflight ON
- quick AI with and without `--skip-preflight`
- balanced AI with and without `--skip-preflight`
- `AI_ENABLE_TORCH=0` semantics assertion
- collision check via rapid repeated runs (parallel)

## Results Matrix

| Case | Exit | Result |
|---|---:|---|
| quick gpu,memory,disk (preflight ON) | 0 | PASS |
| quick ai (preflight ON) | 0 | PASS |
| quick ai (`--skip-preflight`) | 0 | PASS |
| balanced ai (preflight ON) | 0 | PASS |
| balanced ai (`--skip-preflight`) | 0 | PASS |
| quick ai with `AI_ENABLE_TORCH=0` | 0 | PASS |
| semantics assert (`torch` disabled state) | 0 | PASS |
| collision check (3 parallel runs) | 0 aggregate | PASS |

## Key Assertions

1. **Preflight ON/OFF behavior**
   - Default runs produced preflight output in `raw/preflight.json`.
   - `--skip-preflight` runs produced preflight status `skipped` (expected).

2. **`AI_ENABLE_TORCH=0` semantics**
   - In `reports/run-20260217-192900-quick-097400786-41bc/raw/ai.json`, torch backend is present as metadata but marked:
     - `status: "skipped"`
     - `disabled: true`
     - `disabled_by: "AI_ENABLE_TORCH"`
   - This is treated as **correct semantics** for explicit backend disable.

3. **Run directory collision resistance**
   - Three rapid parallel invocations created three distinct run dirs:
     - `run-20260217-192900-quick-474236065-6732`
     - `run-20260217-192900-quick-474370596-2460`
     - `run-20260217-192900-quick-474640391-4742`
   - No overwrite/collision observed.

## Notes
- An initial early attempt of `quick gpu,memory,disk` logged a shell anomaly (`PY: No such file or directory`) in `logs/quick_gpu_memory_disk_preflight_on.log`; rerun (`quick_gpu_memory_disk_preflight_on_rerun.log`) passed cleanly with exit 0.

## PASS/FAIL Summary

**Overall: PASS** for the requested Round 2 focused validation matrix.

## Files Produced
- `reports/VALIDATION_MATRIX_V3_R2.md`
- `reports/validation_v3_r2_artifacts/results.tsv`
- `reports/validation_v3_r2_artifacts/logs/*.log`
