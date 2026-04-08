"""
main.py — Bee Pagoda Benchmark CLI entry point.

Usage:
    bee-pagoda [OPTIONS]              (after pip install)
    python main.py [OPTIONS]          (from source)

On Linux/macOS : delegates to run_suite.sh (bash)
On Windows     : delegates to run_suite.ps1 (PowerShell)
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

import checks
import config_loader

app = typer.Typer(
    name="bee-pagoda",
    help="Bee Pagoda Benchmark — cross-platform CPU/GPU/AI/Memory/Storage benchmark suite.",
    add_completion=False,
)

_ROOT = Path(__file__).parent.resolve()
_IS_WINDOWS = platform.system() == "Windows"

_RUN_SUITE_SH  = _ROOT / "run_suite.sh"
_RUN_SUITE_PS1 = _ROOT / "run_suite.ps1"


@app.command()
def run(
    profile: str = typer.Argument("balanced", help="Profile: quick | balanced | deep"),
    categories: Optional[str] = typer.Option(
        None, "--categories", "-c",
        help="Comma-separated categories: cpu,gpu,ai,memory,disk  (default: all)",
    ),
    skip_preflight: bool = typer.Option(False, "--skip-preflight", help="Skip dependency check"),
    python: Optional[str] = typer.Option(None, "--python", help="Explicit Python interpreter path"),
    check_only: bool = typer.Option(False, "--check-only", help="Run dependency check and exit"),
) -> None:
    """Run the benchmark suite."""

    # ── Dependency check ───────────────────────────────────────────────
    if not checks.verify_deps(verbose=True):
        typer.echo("[ERROR] Required dependencies missing. See above for install instructions.", err=True)
        raise typer.Exit(code=1)

    if check_only:
        raise typer.Exit(code=0)

    # ── Validate profile ───────────────────────────────────────────────
    profile_file = _ROOT / "profiles" / f"{profile}.env"
    if not profile_file.exists():
        available = sorted(p.stem for p in (_ROOT / "profiles").glob("*.env"))
        typer.echo(f"[ERROR] Profile '{profile}' not found.", err=True)
        typer.echo(f"        Available profiles: {', '.join(available)}", err=True)
        raise typer.Exit(code=2)

    # ── Build command ──────────────────────────────────────────────────
    if _IS_WINDOWS:
        cmd = _build_windows_cmd(profile, categories, skip_preflight, python)
    else:
        cmd = _build_linux_cmd(profile, categories, skip_preflight, python)

    typer.echo(f"[INFO] Profile  : {profile}")
    typer.echo(f"[INFO] Platform : {platform.system()}")
    if categories:
        typer.echo(f"[INFO] Categories: {categories}")

    # ── Launch ─────────────────────────────────────────────────────────
    env = os.environ.copy()
    if python:
        env["BENCH_PYTHON"] = python

    try:
        proc = subprocess.run(cmd, env=env, cwd=str(_ROOT))
        raise typer.Exit(code=proc.returncode)
    except KeyboardInterrupt:
        typer.echo("\n[INFO] Benchmark cancelled.", err=True)
        raise typer.Exit(code=130)
    except FileNotFoundError as exc:
        typer.echo(f"[ERROR] Could not launch benchmark suite: {exc}", err=True)
        typer.echo(_suite_not_found_hint(), err=True)
        raise typer.Exit(code=1)


def _build_linux_cmd(
    profile: str,
    categories: Optional[str],
    skip_preflight: bool,
    python: Optional[str],
) -> list:
    if not _RUN_SUITE_SH.exists():
        raise FileNotFoundError(f"run_suite.sh not found at {_RUN_SUITE_SH}")
    cmd = ["bash", str(_RUN_SUITE_SH), profile]
    if categories:
        cmd += ["--categories", categories]
    if skip_preflight:
        cmd.append("--skip-preflight")
    if python:
        cmd += ["--python", python]
    return cmd


def _build_windows_cmd(
    profile: str,
    categories: Optional[str],
    skip_preflight: bool,
    python: Optional[str],
) -> list:
    if not _RUN_SUITE_PS1.exists():
        raise FileNotFoundError(f"run_suite.ps1 not found at {_RUN_SUITE_PS1}")
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(_RUN_SUITE_PS1),
        "-Profile", profile,
    ]
    if categories:
        cmd += ["-Categories", categories]
    if skip_preflight:
        cmd.append("-SkipPreflight")
    if python:
        cmd += ["-Python", python]
    return cmd


def _suite_not_found_hint() -> str:
    if _IS_WINDOWS:
        return (
            "Expected run_suite.ps1 in the repository root.\n"
            "Make sure you cloned the full repository."
        )
    return (
        "Expected run_suite.sh in the repository root.\n"
        "Make sure you cloned the full repository and bash is installed."
    )


if __name__ == "__main__":
    app()
