# AGENT_LOOP_PLAN.md

## Goal
Close current AI/preflight quality gaps and stabilize the multi-agent workflow so programmer/software-engineer/validator roles can execute repeatably with clear handoffs.

## Scope (Current Gaps)
1. `llama-bench` discovery fails even when binary exists.
2. Torch unsupported on Python 3.14 is not messaged clearly/actionably.
3. `nvcc` version parsing can report `2005` instead of CUDA version.
4. AI metric labeling can be read as a single “real” benchmark score when it is a mixed synthetic+native composite.
5. Dev loop lacks strict role contract and quality gates.

---

## Architecture-Level Execution Plan

### Phase 0 — Baseline & Repro Harness (same day)
**Objective:** lock reproducible failing cases before modifying behavior.

- Add/refresh reproducible commands in `docs/KNOWN_GAPS.md` (or new tracker section) for each gap.
- Capture one failing artifact bundle in `reports/` that demonstrates all known issues.
- Define explicit “before/after” grep checks for logs and JSON outputs.

**Exit criteria:** each gap has a deterministic repro command + expected current failure signature.

---

### Phase 1 — Detection/Parsing Reliability Fixes (high priority)

#### 1A. llama-bench discovery hardening
**Implementation direction:**
- Centralize llama discovery in a shared helper (Bash function or Python utility) used by both:
  - `scripts/preflight_check.sh`
  - `scripts/bench_ai.sh`
- Search order should be deterministic and include:
  1. explicit env override (new `LLAMA_BENCH_PATH`)
  2. `PATH` candidates (`llama-bench`, `llama.cpp-bench`)
  3. known local paths relative to repo and script path (not only `./llama.cpp/...` from current cwd)
- Always emit resolved absolute path in notes.

**Acceptance criteria:**
- If binary exists and executable in any supported location, both preflight and AI bench report it as found.
- Running from a different working directory still resolves the same binary.

**Test commands:**
```bash
cd /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool
./scripts/preflight_check.sh /tmp/pf.json /tmp/pf.csv
jq '.checks[] | select(.name=="llama-bench") | {status,path,notes}' /tmp/pf.json

AI_ENABLE_LLAMA=1 AI_ENABLE_TORCH=0 AI_ENABLE_ONNXRUNTIME=0 ./run_suite.sh quick ai
jq '.backend_results[] | select(.backend=="llama.cpp") | {status,notes,model}' reports/run-*/raw/ai.json | tail -n 20
```

#### 1B. nvcc parsing fix
**Implementation direction:**
- Replace generic first-number regex extraction for `nvcc` with command-specific parsing:
  - Prefer `release X.Y` from `nvcc --version` output.
  - Fallback to `Vx.y.z` token if needed.
- Keep generic parser for other commands.

**Acceptance criteria:**
- `nvcc` reports CUDA semantic version (e.g., `12.6`) and never `2005`/copyright year.

**Test commands:**
```bash
./scripts/preflight_check.sh /tmp/pf.json /tmp/pf.csv
jq '.checks[] | select(.name=="nvcc") | {status,version,notes}' /tmp/pf.json
```

---

### Phase 2 — AI Backend Messaging & Semantics (high priority)

#### 2A. Torch on Python 3.14 explicit unsupported messaging
**Implementation direction:**
- In torch backend path, detect interpreter version and import/install error class.
- If Python >= 3.14 and torch unavailable, return `skipped` with explicit note:
  - “PyTorch wheels unavailable for Python 3.14 in this environment; use Python 3.12/3.13 venv for torch backend.”
- Mirror same messaging in preflight `torch` check notes.

**Acceptance criteria:**
- On Python 3.14 + missing torch, output note is actionable (version + remediation), not generic “not installed”.

**Test commands:**
```bash
python3 -V
./scripts/preflight_check.sh /tmp/pf.json /tmp/pf.csv
jq '.checks[] | select(.name=="torch") | {status,notes}' /tmp/pf.json

AI_ENABLE_LLAMA=0 AI_ENABLE_TORCH=1 AI_ENABLE_ONNXRUNTIME=0 ./run_suite.sh quick ai
jq '.backend_results[] | select(.backend=="torch") | {status,notes}' reports/run-*/raw/ai.json | tail -n 20
```

#### 2B. AI metric labeling to prevent synthetic-score confusion
**Implementation direction:**
- Rename top-level AI summary metric fields to distinguish aggregate helper vs native throughput:
  - `primary_metric: composite_normalized_helper` (or equivalent explicit name)
  - add `score_semantics` block with `not_cross_model_comparable: true` and synthetic caveats.
- In Markdown report, add separate sections:
  - “Native backend metrics (source of truth)”
  - “Composite helper index (normalized, capped, synthetic-influenced)”
- Ensure backend rows indicate benchmark type: `native` vs `synthetic_proxy`.

**Acceptance criteria:**
- A reader cannot mistake composite for raw throughput.
- AI report text explicitly marks torch/onnx microbench as synthetic proxy.

**Test commands:**
```bash
./run_suite.sh quick ai
LATEST="$(ls -td reports/run-* | head -n1)"
jq '{primary_metric,notes,composite,backend_results}' "$LATEST/raw/ai.json"
grep -n "Composite helper\|synthetic\|source of truth" "$LATEST/report/summary.md"
```

---

### Phase 3 — Role-Based Multi-Agent Dev Loop (stabilization)

## Role Contract

### Programmer (implementation)
- Makes smallest code changes to satisfy backlog item acceptance criteria.
- Must include/update tests and commands in PR notes.
- Must not redefine requirements.

### Software-Engineer (integration)
- Reviews cross-script consistency, config compatibility, and report schema impacts.
- Ensures backward compatibility (README + profiles + output artifacts).
- Owns refactors shared across scripts.

### Validator (verification)
- Runs prescribed command matrix and checks outputs against acceptance criteria.
- Performs negative tests (missing dependency, wrong cwd, disabled backend).
- Produces pass/fail with evidence paths.

## Loop States (enforced)
1. `SPEC_LOCK` → architect defines acceptance criteria + test commands.
2. `IMPLEMENT` → programmer delivers patch.
3. `INTEGRATE` → software-engineer resolves cross-cutting issues.
4. `VALIDATE` → validator executes test matrix.
5. `MERGE` only if validator pass is explicit.

## Required Artifacts Per Item
- change summary
- files changed
- commands run
- output evidence (`jq`/`grep` snippets + report paths)
- residual risks

---

## Prioritized Backlog (with acceptance + tests)

## P0 (Do first)

### P0-1: Unified llama-bench resolver
**Why:** false-negative discovery blocks core AI path.
**Acceptance criteria:**
- Shared resolver used by preflight + AI bench.
- Supports env override + path + repo-relative lookup.
- Returns absolute path and consistent notes.
**Validation commands:**
```bash
LLAMA_BENCH_PATH="/abs/path/to/llama-bench" ./scripts/preflight_check.sh /tmp/pf.json /tmp/pf.csv
jq '.checks[] | select(.name=="llama-bench")' /tmp/pf.json
```

### P0-2: nvcc version parser specialization
**Why:** wrong CUDA version undermines trust in preflight.
**Acceptance criteria:**
- nvcc parser extracts `release`/`V` semantic version.
- No year-like false matches.
**Validation commands:**
```bash
./scripts/preflight_check.sh /tmp/pf.json /tmp/pf.csv
jq -r '.checks[] | select(.name=="nvcc") | .version' /tmp/pf.json
```

### P0-3: Torch Python 3.14 unsupported note
**Why:** users need clear remediation path.
**Acceptance criteria:**
- Explicit unsupported message shown in preflight + AI backend result when applicable.
- Message includes suggested Python version range for torch backend.
**Validation commands:**
```bash
python3 -V
AI_ENABLE_LLAMA=0 AI_ENABLE_TORCH=1 AI_ENABLE_ONNXRUNTIME=0 ./run_suite.sh quick ai
LATEST="$(ls -td reports/run-* | head -n1)"
jq '.backend_results[] | select(.backend=="torch") | .notes' "$LATEST/raw/ai.json"
```

## P1 (Next)

### P1-1: AI summary labeling/schema clarity
**Why:** prevent misuse of composite helper as absolute performance score.
**Acceptance criteria:**
- Top-level AI JSON + markdown clearly separate helper composite vs backend native metrics.
- Synthetic proxy backends explicitly labeled.
**Validation commands:**
```bash
./run_suite.sh quick ai
LATEST="$(ls -td reports/run-* | head -n1)"
jq '.primary_metric,.composite,.backend_results[]|{backend,benchmark,primary_metric,notes}' "$LATEST/raw/ai.json"
```

### P1-2: Report generator wording hardening
**Why:** user-facing report must communicate caveats consistently.
**Acceptance criteria:**
- `summary.md` contains caution text on comparability and synthetic proxies.
- no ambiguous “AI score” phrasing without qualifier.
**Validation commands:**
```bash
grep -n "synthetic\|proxy\|composite helper\|not cross-model comparable" "$(ls -td reports/run-* | head -n1)/report/summary.md"
```

## P2 (Stabilization)

### P2-1: Formalize role loop template docs/checklist
**Why:** reduce ping-pong and undefined ownership between agents.
**Acceptance criteria:**
- Add reusable checklist template for Programmer / Software-Engineer / Validator outputs.
- Include mandatory evidence snippets and fail-fast rules.
**Validation commands:**
```bash
grep -n "SPEC_LOCK\|IMPLEMENT\|INTEGRATE\|VALIDATE\|MERGE" docs/AGENT_LOOP_PLAN.md
```

---

## Suggested Execution Order (2-pass)

### Pass A (Reliability)
P0-1 → P0-2 → P0-3, then validator run on quick AI + preflight.

### Pass B (Clarity + Workflow)
P1-1 → P1-2 → P2-1, then validator run on quick + balanced AI category and full report text scan.

---

## Final Validation Matrix (must pass before close)

```bash
cd /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool

# preflight sanity
./scripts/preflight_check.sh /tmp/pf.json /tmp/pf.csv
jq '.status,.status_counts' /tmp/pf.json

# AI-only quick
./run_suite.sh quick ai
LATEST="$(ls -td reports/run-* | head -n1)"
jq '.status,.primary_metric,.backend_results' "$LATEST/raw/ai.json"

# Full quick smoke
./run_suite.sh quick
LATEST="$(ls -td reports/run-* | head -n1)"
ls "$LATEST/raw" "$LATEST/report"
```

## Definition of Done
- All P0 and P1 backlog items validated with command evidence.
- No regressions to existing profile/category invocation behavior.
- Report language unambiguously separates native metrics from synthetic/composite helper values.
- Role loop checklist is adopted for subsequent passes.
