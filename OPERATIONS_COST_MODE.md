# OPERATIONS_COST_MODE.md

Compact guide for running this benchmark suite with predictable **runtime + token/cost** usage.

## 1) Pick the Run Depth

| Mode | Use when | Runtime/Cost | Default command |
|---|---|---|---|
| **quick** | Fast sanity check, CI smoke, dependency checks | Lowest | `./run_suite.sh quick` |
| **balanced** | Normal day-to-day comparisons | Medium | `./run_suite.sh balanced` |
| **deep** | Final validation, publishable numbers, variance reduction | Highest | `./run_suite.sh deep` |

Rule of thumb:
- Start with **quick**.
- Escalate to **balanced** only if quick passes and decisions depend on more stable data.
- Use **deep** only for sign-off/regression baselines.

---

## 2) Low-Cost Command Presets

## A. Cheapest health check (no benchmark work)
```bash
./scripts/preflight_check.sh
```
Use to verify tools/dependencies before any expensive run.

## B. Cheap smoke run (CPU + memory + disk only)
```bash
./run_suite.sh quick cpu,memory,disk
```
Skips AI/GPU paths; best first-pass for host sanity.

## C. AI-only quick validation
```bash
./run_suite.sh quick ai
```
Use when changing AI scripts/reporting.

## D. GPU-only quick validation
```bash
./run_suite.sh quick gpu
```
Use when changing GPU compute/game wrappers.

## E. Balanced full suite (default operational baseline)
```bash
./run_suite.sh balanced
```

## F. Deep sign-off (only when needed)
```bash
./run_suite.sh deep
```

## G. Emergency budget mode (short AI + no llama)
```bash
AI_ENABLE_LLAMA=0 AI_ENABLE_TORCH=1 AI_ENABLE_ONNXRUNTIME=1 \
AI_PROMPT_TOKENS=128 AI_GEN_TOKENS=32 AI_BATCH_SIZE=128 AI_CONTEXT_SIZE=1024 \
./run_suite.sh quick ai
```
Useful when you need trend direction, not absolute model throughput.

---

## 3) Profile Intent (quick / balanced / deep)

Based on `profiles/*.env`:
- **quick**: shortest durations, `RUN_REPETITIONS=1`, smaller AI token/context sizes, smaller storage test sizes.
- **balanced**: moderate durations, broader representativeness, still `RUN_REPETITIONS=1`.
- **deep**: long durations, larger AI sizes, `RUN_REPETITIONS=3` for stability.

Decision policy:
1. **Development loop**: quick + scoped categories.
2. **Integration check**: balanced on affected categories.
3. **Release/sign-off**: deep only for target categories (or full suite if required).

---

## 4) Token/Cost-Saving Workflow for Agent Loops

Use this loop to minimize LLM/tool spend:

1. **Spec lock (one short plan)**
   - Define acceptance criteria + exact commands once.
   - Avoid repeated re-planning turns.

2. **Narrow scope first**
   - Run only impacted categories (`cpu`, `gpu`, `ai`, `memory`, `disk`).
   - Avoid full-suite runs during early debugging.

3. **Artifact-first debugging**
   - Read only latest run folder (`reports/run-*/raw/*.json`, `report/summary.md`).
   - Quote targeted snippets (`jq`, `grep`) instead of re-running benchmarks.

4. **Escalation gates**
   - Gate progression: `quick scoped` -> `balanced scoped` -> `deep/fullsuite`.
   - Do not jump to deep unless a gate requires it.

5. **Reuse environment and interpreter**
   - Pin interpreter once with `--python` when needed.
   - Keep dependency churn low; use preflight to detect missing tools instead of trial runs.

6. **Avoid redundant runs**
   - If only docs/report wording changed, do not rerun deep benchmarks.
   - Reuse most recent valid artifacts for narrative/report edits.

7. **Keep prompts compact in multi-agent workflows**
   - Pass: objective, constraints, exact files, validation commands.
   - Avoid large pasted logs unless specifically needed for diagnosis.

---

## 5) Practical Playbooks

## Fast dev iteration (lowest cost)
```bash
./scripts/preflight_check.sh
./run_suite.sh quick <affected-categories>
```

## Pre-merge confidence
```bash
./run_suite.sh balanced <affected-categories>
```

## Release confidence (expensive; last step)
```bash
./run_suite.sh deep <affected-categories>
# or full suite only if required by policy
./run_suite.sh deep
```

---

## 6) Defaults That Keep Cost Predictable

- Prefer `quick` unless a decision requires higher confidence.
- Prefer scoped categories over full suite.
- Treat `deep` as an exception path, not default.
- Use preflight and artifact inspection to replace unnecessary reruns.
