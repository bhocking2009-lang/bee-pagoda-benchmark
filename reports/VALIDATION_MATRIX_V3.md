# VALIDATION_MATRIX_V3

Date: 2026-02-17 (EST)
Validator session: `bench-v3-validator`
Project: `/home/openclaw/.openclaw/workspace/project-linux-benchmark-tool`

## Scope
Validated requested scenarios:
- `quick ai`
- `quick gpu,memory,disk`
- `balanced ai`
- each with and without `--skip-preflight`
- `AI_ENABLE_TORCH=0` variants for AI scenarios

Raw validator artifacts:
- Matrix run bundle: `reports/validation-v3-20260217-185640/`
- Command/exit ledger: `reports/validation-v3-20260217-185640/results.tsv`
- Per-case command logs: `reports/validation-v3-20260217-185640/*.log`

## Other agents status at validation time
`subagents list` showed other active runs (`bench-v3-software-engineer`, `bench-v3-programmer`, `bench-v3-architect`).
Validation is against latest available state during concurrent edits; retest items are listed below.

## Validation matrix

| Case | Command | Expected | Observed | Verdict | Evidence |
|---|---|---|---|---|---|
| quick_ai_preflight_on | `./run_suite.sh quick ai` | exit `0`; AI semantics valid; preflight included | exit `0`; preflight=`degraded`; AI=`skipped` (all backends skipped on missing deps) | PASS | log `reports/validation-v3-20260217-185640/quick_ai_preflight_on.log`; summary `reports/run-20260217-185640-quick/report/summary.json`; raw AI `reports/run-20260217-185640-quick/raw/ai.json` |
| quick_ai_preflight_off | `./run_suite.sh quick ai --skip-preflight` | exit `0`; preflight omitted/skipped | exit `0`; preflight=`skipped`; AI=`skipped` | PASS | log `reports/validation-v3-20260217-185640/quick_ai_preflight_off.log`; summary `reports/run-20260217-185646-quick/report/summary.json` |
| quick_ai_torch0_preflight_on | `AI_ENABLE_TORCH=0 ./run_suite.sh quick ai` | exit `0`; torch backend note should be `disabled by AI_ENABLE_TORCH=0` | exit `0`; torch backend note remained `torch package not installed` (toggle not reflected) | FAIL (semantic) | log `reports/validation-v3-20260217-185640/quick_ai_torch0_preflight_on.log`; raw AI `reports/run-20260217-185647-quick/raw/ai.json` |
| quick_ai_torch0_preflight_off | `AI_ENABLE_TORCH=0 ./run_suite.sh quick ai --skip-preflight` | exit `0`; torch backend disabled semantics | exit `0`; torch backend note still `torch package not installed` | FAIL (semantic) | log `reports/validation-v3-20260217-185640/quick_ai_torch0_preflight_off.log`; raw AI `reports/run-20260217-185653-quick/raw/ai.json` |
| quick_gpu_memory_disk_preflight_on | `./run_suite.sh quick gpu,memory,disk` | exit `0`; category run succeeds | exit `2`; shell parse error `run_suite.sh: line 202: unexpected EOF while looking for matching '"'` | FAIL (exit + runtime error) | log `reports/validation-v3-20260217-185640/quick_gpu_memory_disk_preflight_on.log` |
| quick_gpu_memory_disk_preflight_off | `./run_suite.sh quick gpu,memory,disk --skip-preflight` | exit `0`; category run succeeds | exit `0`; report generated | PASS | log `reports/validation-v3-20260217-185640/quick_gpu_memory_disk_preflight_off.log`; summary `reports/run-20260217-190620-quick/report/summary.json` |
| balanced_ai_preflight_on | `./run_suite.sh balanced ai` | exit `0`; AI semantics valid; preflight included | exit `0`; preflight=`degraded`; AI=`degraded` | PASS | log `reports/validation-v3-20260217-185640/balanced_ai_preflight_on.log`; summary `reports/run-20260217-191533-balanced/report/summary.json`; raw AI `reports/run-20260217-191533-balanced/raw/ai.json` |
| balanced_ai_preflight_off | `./run_suite.sh balanced ai --skip-preflight` | exit `0`; preflight skipped | exit `0`; report dir timestamp collided with next case (`run-20260217-191540-balanced`) | INCONCLUSIVE (artifact collision) | log `reports/validation-v3-20260217-185640/balanced_ai_preflight_off.log`; shared report path `reports/run-20260217-191540-balanced/report/summary.json` |
| balanced_ai_torch0_preflight_on | `AI_ENABLE_TORCH=0 ./run_suite.sh balanced ai` | exit `0`; torch backend disabled semantics | exit `0`; same report dir collision as previous case, semantics not attributable | INCONCLUSIVE (needs isolated rerun) | log `reports/validation-v3-20260217-185640/balanced_ai_torch0_preflight_on.log`; shared report path `reports/run-20260217-191540-balanced/report/summary.json` |
| balanced_ai_torch0_preflight_off | `AI_ENABLE_TORCH=0 ./run_suite.sh balanced ai --skip-preflight` | exit `0`; torch backend disabled semantics | exit `0`; preflight=`skipped`; AI=`degraded`; torch note still `torch package not installed` | FAIL (semantic) | log `reports/validation-v3-20260217-185640/balanced_ai_torch0_preflight_off.log`; summary `reports/run-20260217-191547-balanced/report/summary.json`; raw AI `reports/run-20260217-191547-balanced/raw/ai.json` |

## Findings summary
- Exit-code behavior:
  - Most scenarios returned expected `0`.
  - `quick gpu,memory,disk` with preflight ON returned `2` due shell parse error (hard failure).
- Report semantics:
  - `--skip-preflight` correctly marks preflight as `skipped` where isolated artifacts were produced.
  - `AI_ENABLE_TORCH=0` semantics did **not** appear in produced raw AI output; torch backend remained reported as `torch package not installed` instead of `disabled by AI_ENABLE_TORCH=0`.
- Artifact collision issue:
  - Two back-to-back runs produced identical second-level timestamp directory (`run-20260217-191540-balanced`), causing evidence collision and inconclusive attribution.

## Pending retest items
1. Re-run `balanced ai --skip-preflight` and `AI_ENABLE_TORCH=0 balanced ai` with enforced unique run IDs/timestamps (sleep >=1s or higher-resolution naming) to remove collision.
2. Re-test `quick gpu,memory,disk` with preflight ON after stabilizing latest script state (concurrent agents were active during this validation and observed parse error may have been from transient in-flight edits).
3. Re-test `AI_ENABLE_TORCH=0` semantics on a host with torch installed to disambiguate whether env override is ignored by profile sourcing vs masked by missing dependency.
