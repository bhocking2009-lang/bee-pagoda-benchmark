"""
PreflightService: check which benchmark dependencies are installed.

On Linux:   runs scripts/preflight_check.sh
On Windows: runs scripts/windows/preflight_check.ps1

Both scripts write a JSON file with the same schema so the GUI can show
a unified dependency status view.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.core.schemas import PreflightResult

log = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"
_ROOT = Path(__file__).parent.parent.parent

_PREFLIGHT_SH  = _ROOT / "scripts" / "preflight_check.sh"
_PREFLIGHT_PS1 = _ROOT / "scripts" / "windows" / "preflight_check.ps1"


class PreflightService:
    """Run the preflight check and return a PreflightResult."""

    def run(self, python_bin: Optional[str] = None) -> PreflightResult:
        """
        Execute the platform-appropriate preflight script.

        Falls back to a minimal synthetic result if the script is not found
        or fails to execute.
        """
        if _IS_WINDOWS:
            return self._run_windows(python_bin)
        return self._run_linux(python_bin)

    # ------------------------------------------------------------------
    # Linux path
    # ------------------------------------------------------------------

    def _run_linux(self, python_bin: Optional[str]) -> PreflightResult:
        if not _PREFLIGHT_SH.exists():
            log.warning("preflight_check.sh not found at %s", _PREFLIGHT_SH)
            return self._unavailable("preflight_check.sh not found")

        env_extra: dict = {}
        if python_bin:
            env_extra["BENCH_PYTHON"] = python_bin

        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "preflight.json"
            out_csv  = Path(tmp) / "preflight.csv"

            env = {**os.environ, **env_extra}

            try:
                result = subprocess.run(
                    ["bash", str(_PREFLIGHT_SH), str(out_json), str(out_csv)],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode not in (0, 1):
                    log.warning("preflight_check.sh returned %d", result.returncode)
            except subprocess.TimeoutExpired:
                return self._unavailable("preflight check timed out")
            except Exception as exc:
                return self._unavailable(f"preflight execution failed: {exc}")

            return self._load_json(out_json)

    # ------------------------------------------------------------------
    # Windows path
    # ------------------------------------------------------------------

    def _run_windows(self, python_bin: Optional[str]) -> PreflightResult:
        if not _PREFLIGHT_PS1.exists():
            log.warning("preflight_check.ps1 not found at %s", _PREFLIGHT_PS1)
            return self._unavailable("scripts/windows/preflight_check.ps1 not found")

        env_extra: dict = {}
        if python_bin:
            env_extra["BENCH_PYTHON"] = python_bin

        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "preflight.json"

            env = {**os.environ, **env_extra}

            try:
                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy", "Bypass",
                        "-File", str(_PREFLIGHT_PS1),
                        "-OutJson", str(out_json),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                if result.returncode not in (0, 1):
                    log.warning("preflight_check.ps1 returned %d: %s",
                                result.returncode, result.stderr[:200])
            except subprocess.TimeoutExpired:
                return self._unavailable("preflight check timed out")
            except Exception as exc:
                return self._unavailable(f"preflight execution failed: {exc}")

            return self._load_json(out_json)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_json(out_json: Path) -> "PreflightResult":
        if out_json.exists():
            try:
                with open(out_json, encoding="utf-8") as fh:
                    data = json.load(fh)
                return PreflightResult.from_dict(data)
            except Exception as exc:
                log.warning("Failed to parse preflight JSON: %s", exc)
        return PreflightService._unavailable("preflight JSON output missing or invalid")

    @staticmethod
    def _unavailable(reason: str) -> PreflightResult:
        return PreflightResult(
            status="skipped",
            notes=reason,
        )

    @staticmethod
    def check_tool(name: str) -> bool:
        """Quick check: is *name* on PATH?"""
        return shutil.which(name) is not None
