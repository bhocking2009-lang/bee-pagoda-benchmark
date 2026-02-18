# Bee Pagoda Benchmark UI — MVP Product/UX Spec (Implementable)

Date: 2026-02-17  
Owner: Product/UX  
Status: Ready for engineering handoff (CLI-backed MVP)

## 1) Purpose and constraints

This document converts `docs/BRAND_UI_V1_BRIEF.md` into an implementable MVP spec using the **current output schema** (`raw/*.json`, `report/summary.json`, `report/summary.csv`).

Hard constraints:
- **No fabricated metrics** (no inferred GHz/FPS/AI numbers that are not present in JSON).
- Show only values emitted by scripts and report generator.
- Missing values render as `N/A` + reason from `status`/`notes`.
- Keep backend contract as source of truth; UI is a view layer.

## 2) MVP scope (what ships)

### In scope
1. Intro / launch screen (profile + categories + basic toggles + run trigger)
2. Running dashboard (live status + per-domain cards + logs)
3. Results summary (preflight + per-domain result table + export actions)
4. Bee Pagoda visual theme tokens (logo + palette only, no animation-heavy effects)

### Out of scope (post-MVP)
- Historical trend charts
- Internet leaderboard/percentile claims
- New benchmark metrics not currently emitted by scripts
- Complex desktop-only shell lock-in

## 3) Data contract (current schema)

Primary files:
- `report/summary.json` (aggregated run contract)
- `raw/preflight.json` (dependency matrix)
- `raw/{cpu,gpu_compute,gpu_game,ai,memory,disk}.json` (native per-domain detail)
- `report/summary.csv` (export convenience)

Top-level `summary.json` shape:
- `generated_at`
- `profile`
- `run_dir`
- `selected_categories[]`
- `suite_interpreter`
- `preflight{...}`
- `results.{category}{...}`

Canonical status values in current pipeline:
- `ok`, `degraded`, `skipped`, `failed` (+ `missing` when artifact absent)

## 4) Screen-by-screen UX spec

## A) Intro / Launch screen

### Controls
- Profile select: `quick | balanced | deep`
- Category multiselect mapped to CLI:
  - CPU (`cpu`)
  - GPU Compute (`gpu_compute`)
  - Gaming/Graphics (`gpu_game`)
  - AI (`ai`)
  - Memory (`memory`)
  - Storage (`disk`)
- Graphics options panel (only enabled when `gpu_game` selected):
  - mode: `offscreen | interactive | auto`
  - strict toggle (`STRICT_GPU_GAME=1|0`)
- Run button: **Run Test**

### Preflight badge behavior
- If preflight exists, show:
  - status = `preflight.status`
  - counters = `preflight.status_counts.{present,missing,version-mismatch,optional-missing}`
- If not present yet: `N/A (not scanned)`

### Command mapping (MVP launcher)
- Profile + category run:
  - `./run_suite.sh <profile> --categories <csv>`
- Optional preflight skip exposed as advanced toggle only:
  - append `--skip-preflight`

## B) Running dashboard

### Header
- Title: **Bee Pagoda Benchmark**
- Subtitle: **System Benchmark v2.x**
- Run status: derived from live process + latest available JSON statuses
- Elapsed: process runtime clock
- ETA: show only if deterministic estimate available; else `N/A`

### Domain card grid (CPU / GPU Compute / Gaming / AI / Memory / Storage)
Each card shows:
- `status`
- benchmark name
- key metric (single primary + optional secondary)
- notes snippet (first line/segment)

Do not display chart/sparkline if no time-series exists yet. Use status chip instead.

### Log/events panel
- Source: process stdout/stderr (runner output)
- Also append file-detection events (`raw/<cat>.json written`)

## C) Results summary screen

### Required blocks
1. Run metadata
   - `profile`, `generated_at`, `run_dir`, `suite_interpreter`, `selected_categories`
2. Preflight matrix
   - from `preflight.checks[]` with `name/status/version/path/notes`
3. Domain results table/cards
   - category status, benchmark, primary metric/value, notes
4. AI backend drilldown
   - `backend_results[]` rows and data source labels (`real_model` vs `synthetic_proxy`)
5. Composite formula visibility
   - show `results.ai.composite.formula` exactly when present
6. Export actions
   - open/download: `report/summary.md`, `report/summary.json`, `report/summary.csv`

## 5) Data mapping table (UI field -> JSON path)

| UI area | UI field | JSON path | Render rule |
|---|---|---|---|
| Header | Profile | `profile` | plain text |
| Header | Generated at | `generated_at` | UTC timestamp |
| Header | Selected categories | `selected_categories[]` | comma-join |
| Preflight | Status | `preflight.status` | badge by status |
| Preflight | Counts | `preflight.status_counts.*` | integer chips |
| Preflight table | Dependency rows | `preflight.checks[]` | columns: name/type/required/status/version/path/notes |
| CPU card | Status | `results.cpu.status` | required |
| CPU card | Main score | `results.cpu.score` | label from `results.cpu.primary_metric` |
| CPU card | Subtests | `results.cpu.subtests.*` | status + tool + score/elapsed_sec when present |
| GPU Compute card | Status | `results.gpu_compute.status` | required |
| GPU Compute card | Primary metric | `results.gpu_compute.score` | if empty => `N/A` |
| Gaming card | FPS | `results.gpu_game.fps` | empty => `N/A` |
| Gaming card | Frame time | `results.gpu_game.frametime_ms` | empty => `N/A` |
| AI card | Composite score | `results.ai.score` | label helper score |
| AI card | Prompt/Eval TPS | `results.ai.prompt_tps`, `results.ai.eval_tps` | numeric if present |
| AI backend table | Backend rows | `results.ai.backend_results[]` | show backend/status/data_source/score/notes |
| AI formula | Formula text | `results.ai.composite.formula` | render verbatim |
| Memory card | Score | `results.memory.score` | metric label = `primary_metric` |
| Memory card | Subtests | `results.memory.subtests.*` | include threads/block/size when present |
| Storage card | Seq BW | `results.disk.subtests.fio_seq.bw_kib_per_sec` | numeric text |
| Storage card | Rand IOPS | `results.disk.subtests.fio_rand4k.iops` | numeric text |
| Any card | Notes | `results.<cat>.notes` | show raw note string |

## 6) Metric/label policy (anti-fabrication)

1. Label from schema, not hardcoded assumptions:
   - use `primary_metric` to name the displayed primary value.
2. If value absent/empty/null:
   - render `N/A` and include context from `status` or `notes`.
3. Do not back-calculate unsupported metrics.
4. Do not relabel synthetic proxies as real-model inference.
5. Always expose AI backend `data_source` labels.

## 7) UX states and fallback behavior

Per-card state machine:
- `idle` (not selected)
- `queued` (selected, file not yet produced)
- `running` (process active, file pending/updating)
- terminal: `ok | degraded | skipped | failed | missing`

Terminal semantics in UI copy:
- `ok`: Completed with primary path
- `degraded`: Completed with fallback/partial coverage
- `skipped`: Not run due to dependency or config
- `failed`: Attempted and failed
- `missing`: Expected artifact absent

## 8) Visual/theming implementation notes

- Add `ui_theme` config (JSON/YAML) with tokens:
  - `bg.navy`, `accent.cpu.cyan`, `accent.gpu.magenta`, `accent.gaming.amber`, `accent.ai.teal`, `accent.memory.violet`, `accent.storage.blue`, `brand.gold`
- Keep monochrome-safe variant for terminal/screenshot exports.
- Brand assets path: `assets/brand/` (as briefed).

## 9) Engineering milestone plan (staged)

### Milestone 1 — Read-only Results Viewer (fastest validation)
- Input: existing `report/summary.json`
- Deliver: results summary screen + export links + preflight table
- Acceptance:
  - Every displayed value maps to a JSON path in Section 5
  - Empty/null values render `N/A` (no fabricated placeholders)

### Milestone 2 — Launcher + Run Lifecycle shell
- Add intro screen and command builder (`run_suite.sh`)
- Show live logs and status chips during run
- Acceptance:
  - User can run profile + category selection from UI
  - End state matches generated `summary.json` statuses

### Milestone 3 — Running Dashboard polish
- Domain cards with stable layout, status transitions, note surfacing
- AI backend drilldown during/after run
- Acceptance:
  - AI `data_source` visible for each backend
  - No unsupported charts/metrics rendered

### Milestone 4 — Brand pass + QA hardening
- Apply Bee Pagoda theme tokens/logo variants
- Accessibility checks (contrast, readable status colors)
- Schema regression tests against sample `reports/run-*`
- Acceptance:
  - UI survives missing categories and partial artifacts
  - Results match `summary.json` exactly for all categories

## 10) QA checklist (MVP)

- [ ] CPU `compression` failure appears as failed subtest, not hidden
- [ ] GPU game missing FPS shows `N/A` with degraded context note
- [ ] AI shows backend rows and `real_model`/`synthetic_proxy` labels
- [ ] Preflight optional-missing is distinct from missing
- [ ] Exported JSON/CSV/MD paths open correctly from run directory
- [ ] No screen shows invented units or benchmark claims

---

This MVP spec is intentionally constrained to current artifacts so implementation can start immediately without backend schema changes.
