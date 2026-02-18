# AGENT_LOOP_PLAN_R2.md

## Objective
Remediate exactly the three validator findings from:
- `reports/VALIDATION_MATRIX_V3.md`
- `reports/validation-v3-20260217-185640/results.tsv`

Findings in scope:
1. Parse error / exit `2` in `quick gpu,memory,disk` with preflight ON.
2. `AI_ENABLE_TORCH=0` semantic visibility missing in AI JSON.
3. Run directory timestamp collision causing attribution ambiguity.

Out of scope: unrelated preflight/version/parser/report-text issues.

---

## Constraints and design intent
- Preserve existing CLI contract for `run_suite.sh` (`profile`, `categories`, `--skip-preflight`, `--python`).
- Keep JSON schema backward compatible; add fields where needed, do not remove current keys.
- Make validator evidence attributable to a single run invocation without relying on sleeps.

---

## Ordered remediation plan

## R2-1 (P0): Eliminate parse-failure path in preflight-ON category runs
**Problem signature**
- Validator saw: `run_suite.sh: line 202: unexpected EOF while looking for matching '"'`
- Scenario: `./run_suite.sh quick gpu,memory,disk` (preflight ON) exited `2`.

**Likely failure class**
- Shell syntax/quoting break introduced during in-flight edits (validator notes mention concurrent edits).
- Need hard guard so malformed script state is caught pre-validation.

**Implementation actions**
1. Add shell static gate in dev/CI loop:
   - `bash -n run_suite.sh scripts/*.sh`
   - `shellcheck run_suite.sh scripts/*.sh` (non-blocking initially if shellcheck unavailable; blocking where available).
2. Add a smoke test target for this exact command path:
   - `./run_suite.sh quick gpu,memory,disk`
   - Assert exit code `0` and expected output files exist.
3. Add pre-merge check in agent loop: validation cannot proceed if syntax gate fails.

**Acceptance tests**
```bash
cd /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool

bash -n run_suite.sh scripts/*.sh
./run_suite.sh quick gpu,memory,disk
EC=$?
LATEST="$(ls -td reports/run-* | head -n1)"

test "$EC" -eq 0
test -f "$LATEST/raw/preflight.json"
test -f "$LATEST/raw/gpu_compute.json"
test -f "$LATEST/raw/gpu_game.json"
test -f "$LATEST/raw/memory.json"
test -f "$LATEST/raw/disk.json"
```

**Done when**
- No shell parse errors in syntax gate.
- Scenario exits `0` with preflight ON and generates all expected raw artifacts.

---

## R2-2 (P0): Make `AI_ENABLE_TORCH=0` semantics explicit in AI raw JSON
**Problem signature**
- Under torch-disabled env, raw AI backend note still says `torch package not installed`.
- Validator expected semantic note `disabled by AI_ENABLE_TORCH=0` (or equivalent explicit disable reason).

**Design requirement**
- Environment intent must be represented distinctly from dependency absence.
- If torch is disabled by env, that reason must dominate backend status/notes.

**Implementation actions**
1. In AI backend selection/evaluation path (`scripts/bench_ai.sh` and any helper), evaluate env toggle first.
2. Emit explicit backend record when disabled by policy:
   - `status: "skipped"`
   - `notes: "disabled by AI_ENABLE_TORCH=0"`
   - Optional additive field for clarity: `skip_reason: "env_disabled"`.
3. Preserve existing dependency messaging only when toggle is enabled and dependency check actually runs.
4. Ensure behavior is consistent across quick/balanced and with/without preflight.

**Acceptance tests**
```bash
cd /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool

AI_ENABLE_TORCH=0 ./run_suite.sh quick ai
LATEST="$(ls -td reports/run-* | head -n1)"
jq '.backend_results[] | select(.backend=="torch") | {status,notes,skip_reason}' "$LATEST/raw/ai.json"

AI_ENABLE_TORCH=0 ./run_suite.sh balanced ai --skip-preflight
LATEST="$(ls -td reports/run-* | head -n1)"
jq '.backend_results[] | select(.backend=="torch") | {status,notes,skip_reason}' "$LATEST/raw/ai.json"
```

**Pass criteria**
- Torch backend entry exists and reports disabled-by-env semantics (not dependency-missing semantics) in both runs.

---

## R2-3 (P0): Guarantee unique run directory IDs per invocation
**Problem signature**
- Two runs landed in same second-level directory (e.g., `run-20260217-191540-balanced`), making attribution inconclusive.

**Design requirement**
- Each invocation must map to a unique `RUN_DIR` without external sleep.
- Human-readable timestamp should remain, with deterministic uniqueness suffix.

**Implementation actions**
1. Replace second-only naming with high-resolution + entropy, e.g.:
   - `TS="$(date +%Y%m%d-%H%M%S-%N)"` (nanoseconds), or
   - second timestamp + `mktemp -d` suffix / PID-based suffix.
2. Persist invocation metadata for traceability:
   - `run_meta.json` including command, env toggles, start time, pid.
3. Update validator guidance to use captured run_dir from command output/log rather than `ls -t` only.

**Acceptance tests**
```bash
cd /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool

./run_suite.sh balanced ai --skip-preflight
./run_suite.sh balanced ai

# Must produce two distinct run directories
A="$(tail -n 1 reports/validation-v3-20260217-185640/results.tsv 2>/dev/null || true)"
ls -td reports/run-*-balanced | head -n 2

D1="$(ls -td reports/run-*-balanced | sed -n '1p')"
D2="$(ls -td reports/run-*-balanced | sed -n '2p')"
test "$D1" != "$D2"

test -f "$D1/report/summary.json"
test -f "$D2/report/summary.json"
```

**Pass criteria**
- Back-to-back invocations always produce distinct run directories.
- Each run has attributable artifacts and metadata.

---

## Execution order and handoff gates
1. **R2-1 first** (stability gate): no syntax-safe build, no further validation.
2. **R2-3 second** (evidence integrity): ensure subsequent validation is attributable.
3. **R2-2 third** (semantic correctness): fix AI toggle semantics and validate in collision-safe runs.

Rationale:
- R2-1 prevents hard stop failures.
- R2-3 prevents false INCONCLUSIVE outcomes and protects evidence quality.
- R2-2 then verifies domain semantics on reliable artifacts.

---

## Validator rerun matrix (only affected cases)
Re-run exactly these cases after fixes:
1. `./run_suite.sh quick gpu,memory,disk`
2. `AI_ENABLE_TORCH=0 ./run_suite.sh quick ai`
3. `AI_ENABLE_TORCH=0 ./run_suite.sh quick ai --skip-preflight`
4. `./run_suite.sh balanced ai --skip-preflight`
5. `AI_ENABLE_TORCH=0 ./run_suite.sh balanced ai`

Required verdicts:
- Case 1: PASS (exit `0`, no parse/runtime error).
- Cases 2/3/5: PASS (`torch` backend note/reason explicitly env-disabled).
- Case 4/5 pair: PASS with distinct run dirs and unambiguous attribution.

---

## Definition of done
- All three scoped findings are closed with command evidence.
- No INCONCLUSIVE due to run-dir collision.
- No regression to existing category/profile invocation behavior.
