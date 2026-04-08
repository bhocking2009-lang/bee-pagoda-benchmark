#!/usr/bin/env python3
"""Generate benchmark summary reports (JSON, CSV, Markdown).

New in this version:
- Environment fingerprint included in summary.json
- Normalized result schema with health bands (excellent/good/fair/poor/unknown)
- Compare-to-previous report (report/compare-prev.md) when a prior run exists
"""
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
normalized_dir = os.path.join(run_dir, "normalized")
os.makedirs(report_dir, exist_ok=True)
os.makedirs(normalized_dir, exist_ok=True)

all_categories = ["cpu", "gpu_compute", "gpu_game", "ai", "memory", "disk", "stress"]
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

env_fingerprint = None
fp_path = os.path.join(raw_dir, "env_fingerprint.json")
if os.path.exists(fp_path):
    with open(fp_path) as f:
        env_fingerprint = json.load(f)

# ---- Normalize metrics + health bands ----
# Each metric gets a band relative to reasonable reference values.
# Bands: excellent / good / fair / poor / unknown
_BANDS = {
    "cpu_baseline_score": [
        ("excellent", 15000), ("good", 8000), ("fair", 3000), ("poor", 0)
    ],
    "memory_mib_per_sec": [
        ("excellent", 30000), ("good", 15000), ("fair", 5000), ("poor", 0)
    ],
    "disk_seq_bw_kib_per_sec": [
        ("excellent", 3000000), ("good", 1000000), ("fair", 300000), ("poor", 0)
    ],
    "disk_rand_iops": [
        ("excellent", 100000), ("good", 30000), ("fair", 5000), ("poor", 0)
    ],
    "ai_composite": [
        ("excellent", 0.8), ("good", 0.5), ("fair", 0.2), ("poor", 0)
    ],
}


def _band(metric_key: str, value) -> str:
    if value is None or value == "":
        return "unknown"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "unknown"
    bands = _BANDS.get(metric_key, [])
    for label, threshold in bands:
        if v >= threshold:
            return label
    return "poor"


def _safe_float(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


normalized_metrics = {}

# CPU
cpu_r = results.get("cpu", {})
cpu_score = _safe_float(cpu_r.get("score") or (cpu_r.get("subtests", {}).get("baseline", {}) or {}).get("score"))
normalized_metrics["cpu"] = {
    "baseline_score": cpu_score,
    "baseline_score_band": _band("cpu_baseline_score", cpu_score),
    "status": cpu_r.get("status", "missing"),
}

# Memory
mem_r = results.get("memory", {})
mem_score = _safe_float(mem_r.get("score"))
normalized_metrics["memory"] = {
    "read_write_mib_per_sec": mem_score,
    "read_write_mib_per_sec_band": _band("memory_mib_per_sec", mem_score),
    "status": mem_r.get("status", "missing"),
}

# Disk
disk_r = results.get("disk", {})
disk_subtests = disk_r.get("subtests", {})
seq_bw = _safe_float((disk_subtests.get("fio_seq") or {}).get("bw_kib_per_sec") or disk_r.get("score"))
rand_iops = _safe_float((disk_subtests.get("fio_rand4k") or {}).get("iops"))
normalized_metrics["disk"] = {
    "seq_bw_kib_per_sec": seq_bw,
    "seq_bw_band": _band("disk_seq_bw_kib_per_sec", seq_bw),
    "rand_iops": rand_iops,
    "rand_iops_band": _band("disk_rand_iops", rand_iops),
    "status": disk_r.get("status", "missing"),
}

# AI
ai_r = results.get("ai", {})
ai_composite = _safe_float(ai_r.get("score"))
normalized_metrics["ai"] = {
    "composite_normalized": ai_composite,
    "composite_band": _band("ai_composite", ai_composite),
    "data_source": ai_r.get("data_source", "unknown"),
    "status": ai_r.get("status", "missing"),
}

normalized_results = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "run_dir": run_dir,
    "profile": profile,
    "metrics": normalized_metrics,
}

with open(os.path.join(normalized_dir, "results.json"), "w") as f:
    json.dump(normalized_results, f, indent=2)

# ---- Build summary ----
summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "profile": profile,
    "run_dir": run_dir,
    "selected_categories": categories,
    "suite_interpreter": os.environ.get("BENCH_PYTHON") or sys.executable,
    "preflight": preflight,
    "env_fingerprint": env_fingerprint,
    "results": results,
    "normalized": normalized_results,
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

if env_fingerprint:
    md.append("")
    md.append("## Environment")
    md.append("")
    md.append(f"- **Kernel:** {env_fingerprint.get('kernel', 'N/A')}")
    md.append(f"- **Distro:** {env_fingerprint.get('distro', 'N/A')}")
    md.append(f"- **CPU:** {env_fingerprint.get('cpu_model', 'N/A')}")
    md.append(f"- **RAM:** {env_fingerprint.get('ram_mib', 'N/A')} MiB")
    md.append(f"- **GPU:** {env_fingerprint.get('gpu_model', 'N/A')}")
    md.append(f"- **GPU Driver:** {env_fingerprint.get('gpu_driver', 'N/A')}")
    md.append(f"- **Power Governor:** {env_fingerprint.get('power_governor', 'N/A')}")

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
    checks_list = preflight.get("checks", [])
    if checks_list:
        md.append("")
        md.append("| Dependency | Status | Version | Path |")
        md.append("|---|---|---|---|")
        for c in checks_list:
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
    # Stress-specific fields
    if r.get("throttling_detected") not in (None, "", "unknown"):
        key.append(f"throttling={r['throttling_detected']}")
    if r.get("thermal_trend") not in (None, "", "unknown"):
        key.append(f"thermal={r['thermal_trend']}")
    if r.get("notes"):
        key.append(r.get("notes"))
    md.append(f"| {cat} | {r.get('status', '')} | {r.get('benchmark', '')} | {'; '.join(key)} |")

md.append("")
md.append("## Normalized Metrics & Health Bands")
md.append("")
md.append("| Category | Metric | Value | Band |")
md.append("|---|---|---|---|")
for cat, nm in normalized_metrics.items():
    for k, v in nm.items():
        if k == "status" or k.endswith("_band"):
            continue
        band = nm.get(f"{k}_band", "")
        md.append(f"| {cat} | {k} | {v if v is not None else 'N/A'} | {band} |")

md.append("")
md.append("## Exit Semantics")
md.append("- `0`: selected steps completed without `failed` status")
md.append("- `1`: one or more selected benchmark steps failed")
md.append("- `2`: usage/config error")

with open(os.path.join(report_dir, "summary.md"), "w") as f:
    f.write("\n".join(md) + "\n")

# ---- Compare to previous run ----
_compare_lines = []
reports_root = os.path.dirname(run_dir)
prev_summary = None
prev_run_dir = None

try:
    run_dirs = sorted([
        d for d in os.listdir(reports_root)
        if os.path.isdir(os.path.join(reports_root, d)) and d.startswith("run-")
        and os.path.join(reports_root, d) != run_dir
    ])
    if run_dirs:
        prev_run_dir = os.path.join(reports_root, run_dirs[-1])
        prev_summary_path = os.path.join(prev_run_dir, "report", "summary.json")
        if os.path.exists(prev_summary_path):
            with open(prev_summary_path) as f:
                prev_summary = json.load(f)
except Exception:
    pass

if prev_summary:
    prev_results = prev_summary.get("results", {})
    _compare_lines.append("# Compare to Previous Run")
    _compare_lines.append("")
    _compare_lines.append(f"- **Current run:** `{run_dir}`")
    _compare_lines.append(f"- **Previous run:** `{prev_run_dir}`")
    _compare_lines.append(f"- **Previous profile:** `{prev_summary.get('profile', 'N/A')}`")
    _compare_lines.append("")
    _compare_lines.append("| Category | Prev Status | Curr Status | Prev Score | Curr Score | Delta |")
    _compare_lines.append("|---|---|---|---|---|---|")
    for cat in categories:
        curr_r = results.get(cat, {})
        prev_r = prev_results.get(cat, {})
        curr_score = _safe_float(curr_r.get("score"))
        prev_score = _safe_float(prev_r.get("score"))
        if curr_score is not None and prev_score is not None and prev_score != 0:
            delta = f"{(curr_score - prev_score) / prev_score * 100:+.1f}%"
        else:
            delta = "N/A"
        _compare_lines.append(
            f"| {cat} | {prev_r.get('status','N/A')} | {curr_r.get('status','N/A')} "
            f"| {prev_score if prev_score is not None else 'N/A'} "
            f"| {curr_score if curr_score is not None else 'N/A'} | {delta} |"
        )
    with open(os.path.join(report_dir, "compare-prev.md"), "w") as f:
        f.write("\n".join(_compare_lines) + "\n")

print(os.path.join(report_dir, "summary.md"))

# ---- Record run in trend database ----
try:
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from trend_store import record_run
    record_run(run_dir=run_dir, summary=summary)
except Exception:
    pass  # trend recording is best-effort; never block report generation


