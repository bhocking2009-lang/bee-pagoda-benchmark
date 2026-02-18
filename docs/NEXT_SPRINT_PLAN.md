# NEXT_SPRINT_PLAN.md

Date: 2026-02-17  
Owner: Architecture

## Sprint goal (single sentence)
Ship a reliability-first increment that (a) removes remaining CPU compression false failures around `7z`, (b) introduces a non-breaking GPU vendor abstraction path for NVIDIA/AMD/Intel, and (c) lands a minimal UI shell that renders only real benchmark metrics.

---

## Scope and non-goals

### In scope
1. CPU compression stability hardening (`7z b` path) with deterministic failure typing.
2. GPU vendor abstraction scaffolding behind current behavior-preserving adapter.
3. UI shell milestones: launch/run/results views wired to existing report JSON only.

### Out of scope (this sprint)
- New benchmark domains or synthetic “placeholder” metrics.
- Replacing existing GPU command implementations wholesale.
- Full design-system/polish pass beyond functional shell.

---

## Workstream A — CPU compression instability (7z)

## Problem
CPU suite still has residual instability around `7z` execution/results parsing (intermittent fail/low-signal diagnostics).

## Plan
A1. Add `7z` capability probe before timed benchmark.
- Validate executable path/version.
- Run a short probe (`7z b` short timeout) to classify environment readiness.

A2. Normalize and harden `7z` execution.
- Standardize env (`LC_ALL=C`, explicit thread count and timeout wrapper usage).
- Capture explicit reason codes (`7z_missing`, `7z_timeout`, `7z_exit_<code>`, `7z_parse_failed`).

A3. Harden output parsing + fallback metric extraction.
- Prefer known lines for total rating; if parse fails, retain run status but classify metric extraction failure separately.
- Persist raw tail in diagnostics for replay.

A4. Add focused regression script for CPU compression reliability.
- Positive run, constrained env run, forced-failure run (bad binary/path simulation).

### Acceptance tests (A)
1. **Controlled failure classification**
   - Run with invalid `7z` binary override (or PATH exclusion).
   - Expected: compression status `failed` with explicit reason code (not generic failure note).
2. **Constrained shell determinism**
   - Run CPU under `env -i` minimal PATH.
   - Expected: deterministic reason/status and captured `7z` diagnostics.
3. **Healthy host pass**
   - Run CPU quick with known-good `7z`.
   - Expected: compression status `ok`; no ambiguous compression failure note.
4. **Parse robustness**
   - Validate parser against at least 2 real `7z b` output shapes (host/version differences).
   - Expected: score extracted or reason `7z_parse_failed` emitted explicitly.

---

## Workstream B — GPU vendor abstraction roadmap (NVIDIA/AMD/Intel)

## Target architecture
Keep current behavior as default via a compatibility adapter, while introducing a provider interface:
- `GpuProvider` contract: `detect()`, `preflight()`, `run_compute()`, `run_graphics()`, `normalize_metrics()`.
- Providers: `nvidia_provider`, `amd_provider`, `intel_provider`, `generic_provider`.
- Selector: auto-detect vendor from existing signals (`nvidia-smi`, ROCm tools/OpenCL/Vulkan hints, Intel GPU hints).

## Sequenced roadmap (non-breaking)
B1. Introduce provider interface + compatibility wrapper (no behavior change).
- Existing script flow remains source of truth.
- New layer only routes to current commands initially.

B2. Implement vendor detection matrix and telemetry.
- Emit detected vendor + selected provider into raw GPU diagnostics.
- If uncertain, force `generic_provider`.

B3. Add vendor-specific optional probes (best-effort, no hard failure).
- NVIDIA: retain `nvidia-smi` enrichment if present.
- AMD/Intel: add optional enrichment fields when tools are available.

B4. Incremental provider overrides (one by one), guarded by feature flags.
- Default flags keep compatibility path.
- Vendor-native paths opt-in until validated.

### Acceptance tests (B)
1. **No-regression baseline**
   - Existing GPU runs produce same status/exit behavior with abstraction enabled by default compatibility mode.
2. **Provider selection transparency**
   - Raw GPU JSON includes `vendor_detected`, `provider_selected`, `provider_mode`.
3. **Fallback safety**
   - Unknown/mixed vendor environments always fall back to `generic_provider` without run failure caused by detection.
4. **Feature-flag isolation**
   - Enabling/disabling vendor-native provider path changes only provider diagnostics unless vendor path explicitly selected.

---

## Workstream C — Minimal UI shell milestones (real metrics only)

## Rules
- UI may render only fields present in run artifacts (`raw/*.json`, `report/summary.json`).
- Missing fields render as `N/A` + reason/status badge.
- No fabricated units, no synthetic placeholder KPI cards.

## Milestones
C1. **Shell bootstrap (Launch view)**
- Profile/category picker + start action.
- Preflight readiness summary from real preflight output.

C2. **Running view (status-first)**
- Domain tiles (CPU/GPU Compute/GPU Graphics/AI/Memory/Storage) with real status + last known metric.
- Event log tail from runner output/artifacts.

C3. **Results view (truth mirror)**
- Render summary score/status and per-domain metrics exactly as exported report values.
- Export links/actions for markdown/json/csv artifacts.

### Acceptance tests (C)
1. **Schema fidelity**
   - For a completed run, each displayed metric can be mapped to a concrete JSON path in artifacts.
2. **Unavailable data behavior**
   - For a skipped/degraded domain, UI shows `N/A` or degraded badge with reason (no fake number).
3. **Report parity**
   - Results view values match `report/summary.json` for selected sample runs.
4. **Run flow**
   - From launch screen, user starts a `quick` run and reaches results view with non-empty real data.

---

## Sprint sequencing (execution order)

## Week plan
1. **Days 1-2 (P0): Workstream A**
   - Close `7z` instability first; reliability gate for rest of sprint.
2. **Days 3-4 (P0/P1): Workstream B foundation (B1-B2)**
   - Land provider interface + compatibility mode + detection telemetry.
3. **Day 5 (P1): Workstream C C1-C2**
   - Launch/running shell with strict real-metric rendering.
4. **Day 6 (P1): Workstream B3 + C3**
   - Vendor enrichment (optional) + results parity view.
5. **Day 7 (buffer/hardening):**
   - Regression matrix, doc updates, final acceptance sweep.

## Dependency chain
- A must pass before final UI/report parity signoff (CPU tile confidence).
- B1-B2 must land before UI running/results GPU tiles can expose provider metadata.
- C3 depends on stable report schema from current generator (no schema churn late sprint).

---

## Definition of done (sprint)
- CPU compression no longer fails ambiguously; failures are reason-coded and reproducible.
- GPU abstraction layer exists with compatibility default, vendor detection telemetry, and safe fallback path.
- UI shell supports launch/run/results using only real metrics and matches exported report values.
- All acceptance tests above pass on at least one healthy host run + one constrained/failure-injection run.