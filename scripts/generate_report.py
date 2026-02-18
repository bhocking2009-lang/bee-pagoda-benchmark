#!/usr/bin/env python3
import json
import csv
import os
import sys
from datetime import datetime, timezone

if len(sys.argv) not in (3, 4):
    print("Usage: generate_report.py <run_dir> <profile_name> [selected_csv]")
    sys.exit(2)

run_dir = sys.argv[1]
profile = sys.argv[2]
selected = sys.argv[3].split(",") if len(sys.argv) == 4 and sys.argv[3] else []

raw_dir = os.path.join(run_dir, "raw")
report_dir = os.path.join(run_dir, "report")
os.makedirs(report_dir, exist_ok=True)

all_categories = ["cpu", "gpu_compute", "gpu_game", "ai", "memory", "disk"]
categories = selected if selected else [c for c in all_categories if os.path.exists(os.path.join(raw_dir, f"{c}.json"))]
if not categories:
    categories = all_categories

results = {}
for cat in categories:
    p = os.path.join(raw_dir, f"{cat}.json")
    if os.path.exists(p):
        with open(p) as f:
            results[cat] = json.load(f)
    else:
        results[cat] = {"category": cat, "status": "missing", "notes": "raw json not found"}

preflight = None
preflight_path = os.path.join(raw_dir, "preflight.json")
if os.path.exists(preflight_path):
    with open(preflight_path) as f:
        preflight = json.load(f)

summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "profile": profile,
    "run_dir": run_dir,
    "selected_categories": categories,
    "suite_interpreter": os.environ.get("BENCH_PYTHON") or sys.executable,
    "preflight": preflight,
    "results": results,
}

with open(os.path.join(report_dir, "summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

csv_path = os.path.join(report_dir, "summary.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["category", "status", "benchmark", "backend", "primary_metric", "data_source", "score", "fps", "frametime_ms", "prompt_tps", "eval_tps", "model", "context_size", "batch_size", "notes"])
    for cat in categories:
        r = results.get(cat, {})
        w.writerow([
            r.get("category", cat),
            r.get("status", ""),
            r.get("benchmark", ""),
            r.get("backend", ""),
            r.get("primary_metric", ""),
            r.get("data_source", ""),
            r.get("score", ""),
            r.get("fps", ""),
            r.get("frametime_ms", ""),
            r.get("prompt_tps", ""),
            r.get("eval_tps", ""),
            r.get("model", ""),
            r.get("context_size", ""),
            r.get("batch_size", ""),
            r.get("notes", ""),
        ])

status_counts = {"ok": 0, "degraded": 0, "skipped": 0, "failed": 0, "missing": 0}
for r in results.values():
    s = r.get("status", "unknown")
    if s in status_counts:
        status_counts[s] += 1

md = []
md.append("# Linux Benchmark Report")
md.append("")
md.append(f"- **Profile:** `{profile}`")
md.append(f"- **Generated (UTC):** `{summary['generated_at']}`")
md.append(f"- **Run directory:** `{run_dir}`")
md.append(f"- **Selected categories:** `{', '.join(categories)}`")
md.append(f"- **Suite Python interpreter:** `{summary['suite_interpreter']}`")
md.append("")
md.append("## Preflight")
md.append("")
if preflight:
    md.append(f"- status: {preflight.get('status', 'unknown')}")
    counts = preflight.get("status_counts", {})
    if counts:
        md.append(f"- present: {counts.get('present', 0)}")
        md.append(f"- missing: {counts.get('missing', 0)}")
        md.append(f"- version-mismatch: {counts.get('version-mismatch', 0)}")
        md.append(f"- optional-missing: {counts.get('optional-missing', 0)}")
    if preflight.get("interpreter"):
        md.append(f"- interpreter: {preflight.get('interpreter')}")
    if preflight.get("notes"):
        md.append(f"- notes: {preflight.get('notes')}")
    checks = preflight.get("checks", [])
    if checks:
        md.append("")
        md.append("| Dependency | Status | Version | Path |")
        md.append("|---|---|---|---|")
        for c in checks:
            md.append(f"| {c.get('name','')} | {c.get('status','')} | {c.get('version','') or ''} | {c.get('path','') or ''} |")
else:
    md.append("- status: skipped (preflight artifact not found)")

md.append("")
md.append("## Status Summary")
md.append("")
md.append(f"- ok: {status_counts['ok']}")
md.append(f"- degraded: {status_counts['degraded']}")
md.append(f"- skipped: {status_counts['skipped']}")
md.append(f"- failed: {status_counts['failed']}")
md.append(f"- missing: {status_counts['missing']}")
md.append("")
md.append("## Results")
md.append("")
md.append("| Category | Status | Benchmark | Key Metrics |")
md.append("|---|---|---|---|")
for cat in categories:
    r = results[cat]
    key = []
    if r.get("score"):
        key.append(f"score={r['score']}")
    if r.get("fps"):
        key.append(f"fps={r['fps']}")
    if r.get("frametime_ms"):
        key.append(f"frametime_ms={r['frametime_ms']}")
    if r.get("prompt_tps"):
        key.append(f"prompt_tps={r['prompt_tps']}")
    if r.get("eval_tps"):
        key.append(f"eval_tps={r['eval_tps']}")
    if r.get("backend"):
        key.append(f"backend={r['backend']}")
    if r.get("data_source"):
        key.append(f"data_source={r['data_source']}")
    if r.get("model"):
        key.append(f"model={r['model']}")
    if r.get("subtests"):
        for sk, sv in r["subtests"].items():
            key.append(f"{sk}:{sv.get('status', 'unknown')}")
    if r.get("backend_results"):
        labels = []
        for br in r.get("backend_results", []):
            b = br.get("backend", "?")
            ds = br.get("data_source") or ("real_model" if b == "llama.cpp" else "synthetic_proxy")
            labels.append(f"{b}:{ds}:{br.get('status','unknown')}")
        key.append("backend_sources=" + ",".join(labels))
    if r.get("composite", {}).get("formula"):
        key.append(f"composite_formula={r['composite']['formula']}")
    if r.get("notes"):
        key.append(r.get("notes"))
    md.append(f"| {cat} | {r.get('status', '')} | {r.get('benchmark', '')} | {'; '.join(key)} |")

md.append("")
md.append("## Exit Semantics")
md.append("- `0`: selected steps completed without `failed` status")
md.append("- `1`: one or more selected benchmark steps failed")
md.append("- `2`: usage/config error")

with open(os.path.join(report_dir, "summary.md"), "w") as f:
    f.write("\n".join(md) + "\n")

print(os.path.join(report_dir, "summary.md"))
