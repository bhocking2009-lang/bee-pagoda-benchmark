import json
import os
import random
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Optional

import typer

import checks
import config_loader
import plugins_loader

app = typer.Typer(name="bee-pagoda")

_ROOT = os.path.dirname(os.path.abspath(__file__))
_ALL_CATEGORIES = ["cpu", "gpu", "ai", "memory", "disk"]


def _run_dir(profile: str) -> str:
    """Create a unique timestamped run directory under reports/."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = os.path.join(_ROOT, "reports")
    os.makedirs(base, exist_ok=True)
    suffix = f"{random.randint(0, 0xffff):04x}"
    run_dir = os.path.join(base, f"run-{ts}-{profile}-{suffix}")
    os.makedirs(os.path.join(run_dir, "raw"), exist_ok=True)
    return run_dir


@app.command()
def run(
    profile: str = typer.Argument("balanced", help="Profile name (quick/balanced/deep/ai-focus/gaming-focus/storage-focus)"),
    categories: Optional[str] = typer.Option(None, "--categories", "-c", help="Comma-separated categories: cpu,gpu,ai,memory,disk"),
    skip_preflight: bool = typer.Option(False, "--skip-preflight", help="Skip dependency preflight check"),
):
    """Run the Bee Pagoda Benchmark suite."""
    if not skip_preflight:
        if not checks.verify_deps():
            raise typer.Exit(code=3)

    profile_file = os.path.join(_ROOT, "profiles", f"{profile}.env")
    if not os.path.exists(profile_file):
        typer.echo(f"[ERROR] Profile not found: {profile_file}", err=True)
        available = [f.replace(".env", "") for f in os.listdir(os.path.join(_ROOT, "profiles")) if f.endswith(".env")]
        typer.echo(f"Available profiles: {', '.join(sorted(available))}", err=True)
        raise typer.Exit(code=2)

    config = config_loader.load_config(profile_file)
    cats = [c.strip() for c in categories.split(",")] if categories else _ALL_CATEGORIES

    run_dir = _run_dir(profile)
    raw_dir = os.path.join(run_dir, "raw")

    typer.echo(f"[INFO] Run directory: {run_dir}")
    typer.echo(f"[INFO] Profile: {profile}")
    typer.echo(f"[INFO] Categories: {cats}")

    # Progress event stream: emit JSON-lines on stdout for future UI consumption
    def emit_event(event: str, **kwargs):
        data = {"event": event, "ts": datetime.now(timezone.utc).isoformat(), **kwargs}
        print(json.dumps(data), flush=True)

    emit_event("run_start", profile=profile, categories=cats, run_dir=run_dir)

    exit_code = 0
    results: dict = {}

    # Map category names to script-level names and plugin dirs
    cat_map = {
        "cpu": "cpu",
        "gpu": "gpu",
        "gpu_compute": "gpu",
        "gpu_game": "gpu",
        "ai": "ai",
        "memory": "memory",
        "disk": "disk",
        "storage": "disk",
    }

    for cat in cats:
        plugin_dir = cat_map.get(cat, cat)
        emit_event("step_start", category=cat)
        plugins = plugins_loader.load_plugins(plugin_dir)
        if not plugins:
            typer.echo(f"[WARN] No plugins found for category: {cat}", err=True)
            results[cat] = {
                "category": cat,
                "status": "skipped",
                "notes": f"no plugin found for category {cat}",
            }
            emit_event("step_done", category=cat, status="skipped")
            continue

        # Run first matching plugin (each category has one canonical plugin)
        plugin = plugins[0]
        try:
            result = plugin.run(config)
        except Exception as exc:
            result = {
                "category": cat,
                "status": "failed",
                "benchmark": cat,
                "primary_metric": "score",
                "score": None,
                "notes": f"plugin exception: {exc}",
            }

        # Write raw artifact so generate_report.py can read it
        raw_key = cat if cat not in ("gpu", "gpu_compute", "gpu_game") else cat
        raw_path = os.path.join(raw_dir, f"{raw_key}.json")
        with open(raw_path, "w") as f:
            json.dump(result, f, indent=2)

        results[cat] = result
        status = result.get("status", "unknown")
        emit_event("step_done", category=cat, status=status)
        if status == "failed":
            exit_code = 1
        typer.echo(f"[{'OK' if status in ('ok', 'degraded', 'skipped') else 'ERR'}] {cat}: {status}")

    # Generate reports
    python_bin = sys.executable
    selected_csv = ",".join(cats)
    report_proc = subprocess.run(
        [python_bin, os.path.join(_ROOT, "scripts", "generate_report.py"), run_dir, profile, selected_csv],
        capture_output=True,
        text=True,
    )
    if report_proc.returncode == 0:
        report_md = report_proc.stdout.strip()
        typer.echo(f"[OK] Report: {report_md}")
    else:
        typer.echo(f"[WARN] Report generation failed: {report_proc.stderr}", err=True)

    emit_event("run_done", exit_code=exit_code, run_dir=run_dir)
    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()

