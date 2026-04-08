"""
Python wrapper around run_suite.sh (Linux/macOS) or run_suite.ps1 (Windows).

Provides:
  - RunRequest: typed parameters for starting a benchmark run
  - Runner: builds the CLI command and launches via ProcessManager
  - cli_main(): entry point for `bee-pagoda-cli`
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from app.core.process_manager import DoneCallback, LineCallback, ProcessManager

log = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"
_ROOT = Path(__file__).parent.parent.parent
_RUN_SUITE_SH  = _ROOT / "run_suite.sh"
_RUN_SUITE_PS1 = _ROOT / "run_suite.ps1"


@dataclass
class RunRequest:
    profile: str = "balanced"
    categories: List[str] = field(default_factory=list)  # empty = all
    python_bin: Optional[str] = None
    skip_preflight: bool = False
    extra_env: dict = field(default_factory=dict)

    def category_str(self) -> str:
        if not self.categories:
            return "all"
        return ",".join(self.categories)

    def to_cmd(self) -> List[str]:
        if _IS_WINDOWS:
            return self._to_cmd_windows()
        return self._to_cmd_linux()

    def _to_cmd_linux(self) -> List[str]:
        cmd = ["bash", str(_RUN_SUITE_SH), self.profile]
        if self.categories:
            cmd += ["--categories", self.category_str()]
        if self.skip_preflight:
            cmd.append("--skip-preflight")
        if self.python_bin:
            cmd += ["--python", self.python_bin]
        return cmd

    def _to_cmd_windows(self) -> List[str]:
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", str(_RUN_SUITE_PS1),
            "-Profile", self.profile,
        ]
        if self.categories:
            cmd += ["-Categories", self.category_str()]
        if self.skip_preflight:
            cmd.append("-SkipPreflight")
        if self.python_bin:
            cmd += ["-Python", self.python_bin]
        return cmd


class Runner:
    """
    Orchestrates a single benchmark run via the platform-appropriate script.

    On Linux/macOS: run_suite.sh (bash)
    On Windows:     run_suite.ps1 (PowerShell)

    Thread-safe: one active run at a time.  Call start() from any thread;
    callbacks are invoked on the reader thread (use Qt signals in GUI code).
    """

    def __init__(self) -> None:
        self._pm = ProcessManager()

    def start(
        self,
        request: RunRequest,
        on_line: Optional[LineCallback] = None,
        on_done: Optional[DoneCallback] = None,
    ) -> None:
        if self._pm.is_running:
            raise RuntimeError("A benchmark run is already in progress")

        suite_script = _RUN_SUITE_PS1 if _IS_WINDOWS else _RUN_SUITE_SH
        if not suite_script.exists():
            raise FileNotFoundError(
                f"Benchmark orchestrator not found at {suite_script}"
            )

        env = {**request.extra_env}
        cmd = request.to_cmd()
        log.info("Launching: %s", " ".join(cmd))

        self._pm.start(
            cmd=cmd,
            env=env if env else None,
            cwd=str(_ROOT),
            on_line=on_line,
            on_done=on_done,
        )

    def cancel(self) -> None:
        self._pm.terminate()

    def force_stop(self) -> None:
        self._pm.kill()

    def wait(self) -> Optional[int]:
        return self._pm.wait()

    @property
    def is_running(self) -> bool:
        return self._pm.is_running

    @property
    def pid(self) -> Optional[int]:
        return self._pm.pid


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def cli_main() -> None:
    """
    Simple CLI wrapper for the platform-specific benchmark suite.

    Usage: bee-pagoda-cli [profile] [--categories cpu,gpu,...] [--skip-preflight]
           bee-pagoda-cli --help
    """
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        prog="bee-pagoda-cli",
        description="Bee Pagoda Benchmark — CLI runner",
    )
    parser.add_argument("profile", nargs="?", default="balanced",
                        help="Profile name: quick, balanced, deep")
    parser.add_argument("--categories", metavar="CAT,...", default="",
                        help="Comma-separated list: cpu,gpu,gpu_compute,gpu_game,ai,memory,disk")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--python", metavar="PATH", default=None,
                        help="Explicit Python interpreter path")
    args = parser.parse_args()

    cats = [c.strip() for c in args.categories.split(",") if c.strip()] if args.categories else []

    req = RunRequest(
        profile=args.profile,
        categories=cats,
        python_bin=args.python,
        skip_preflight=args.skip_preflight,
    )

    runner = Runner()
    runner.start(req, on_line=print)
    code = runner.wait()
    sys.exit(code or 0)


if __name__ == "__main__":
    cli_main()
