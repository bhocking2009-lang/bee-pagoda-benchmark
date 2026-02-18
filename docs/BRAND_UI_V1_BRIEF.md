# Bee Pagoda Benchmark UI — Product/Brand Brief (v1)

Date: 2026-02-17
Owner: Controller

## 1) Brand direction locked from draft

- **Company/product mark concept:** Bee + Pagoda ("Bee Pagoda")
- **Visual style:** dark navy background, neon accent data viz, premium gold logo treatment
- **Tone:** technical + elegant, not gamer-chaotic
- **Primary color lanes (recommended):**
  - CPU: cyan
  - GPU: magenta
  - Gaming: yellow/orange
  - AI: aqua/teal
  - Memory/Storage: violet/blue

## 2) Screens to implement

## A) Intro / Launch Screen
Purpose: choose benchmark profile + rendering options + start run

Required controls:
- Test selection (Quick / Balanced / Deep + custom categories)
- Resolution selector (when graphics tests enabled)
- Windowed/fullscreen toggle
- Graphics options (ray tracing/DLSS toggles only if test supports)
- Start button
- Preflight status summary (small badge: ready / degraded / missing deps)

## B) Running Dashboard
Purpose: show live progress and real metrics while tests execute

Layout blocks:
- Header logo + run status + elapsed time + ETA
- Tile grid: CPU / GPU Compute / GPU Graphics (Gaming) / AI / Memory / Storage
- Per-tile: status, current test, sparkline, key metric, confidence/status note
- Bottom: logs/events panel + next step queue

## C) Results Summary
Purpose: final report at a glance + drilldown links

Required:
- Overall score bands + per-domain scores
- Preflight findings (present/optional-missing/missing/version mismatch)
- Native metrics table and composite metrics (formula visible)
- Export actions (markdown/json/csv)

## 3) Data realism rules (critical)

Do **not** display fabricated or mismatched units.
Examples to avoid:
- showing "GPU 3.5 GHz" if no such metric is collected
- showing fake FPS for AI

Display only what pipeline actually provides. If unavailable:
- show `N/A` with reason
- mark tile as `skipped` or `degraded`

## 4) Map current real data -> UI fields

From current benchmark outputs:

- CPU tile:
  - score/events_per_sec (sysbench)
  - compression/encode sub-metrics (7z/ffmpeg) when present
- GPU Compute tile:
  - clpeak/hashcat metric (or N/A)
- Gaming tile:
  - fps + frame-time from vkmark/glmark2 when available
  - otherwise degraded with context note
- AI tile:
  - per-backend rows (llama/onnx/torch)
  - backend source labels: `real_model` vs `synthetic_proxy`
  - composite score with explicit formula
- Memory tile:
  - sysbench memory score + tinymembench details
- Storage tile:
  - fio sequential/random scores, latency if available
- Preflight panel:
  - status counts + dependency matrix

## 5) Suggested copy and naming

- Product title: **Bee Pagoda Benchmark**
- Runner subtitle: **System Benchmark v2.x**
- CTA: **Run Test** / **Launch Test**
- Status labels: `ok`, `degraded`, `skipped`, `failed`

## 6) Implementation notes for team

- Use the same JSON schema as report generator to drive UI (single source of truth).
- Separate brand assets from metrics layer.
- Add a `ui_theme` config file for palette/logo variants.
- Keep intro and running dashboard functional with CLI-only backend first (no heavy desktop framework lock yet).

## 7) Asset direction

- Keep multiple bee-pagoda logo variants under `assets/brand/`.
- Select one as primary lockup after usability pass.
- Ensure monochrome fallback for terminal/report contexts.

## 8) Acceptance criteria for v1 UI shell

1. Intro screen launches chosen benchmark profile.
2. Running dashboard updates live with actual test statuses.
3. No fabricated metrics; all units tied to real fields.
4. Results summary matches exported report values.
5. Branding uses bee-pagoda motif consistently.

## 9) Implementation handoff

- Implementable MVP details and explicit schema mappings are documented in:
  - `docs/UI_MVP_SPEC.md`
