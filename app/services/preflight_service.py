"""
PreflightService: check which benchmark dependencies are installed.

Runs scripts/preflight_check.sh and parses the resulting JSON so the GUI
can show a dependency status view without blocking the main thread.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.core.schemas import PreflightResult

log = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent.parent
_PREFLIGHT_SCRIPT = _ROOT / "scripts" / "preflight_check.sh"


class PreflightService:
    """Run the preflight check and return a PreflightResult."""

    def run(self, python_bin: Optional[str] = None) -> PreflightResult:
        """
        Execute preflight_check.sh and return parsed results.

        Falls back to a minimal synthetic result if the script is not found
        or fails to execute.
        """
        if not _PREFLIGHT_SCRIPT.exists():
            log.warning("preflight_check.sh not found at %s", _PREFLIGHT_SCRIPT)
            return self._unavailable("preflight_check.sh not found")

        env_extra: dict = {}
        if python_bin:
            env_extra["BENCH_PYTHON"] = python_bin

        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "preflight.json"
            out_csv = Path(tmp) / "preflight.csv"

            import os
            env = {**os.environ, **env_extra}

            try:
                result = subprocess.run(
                    ["bash", str(_PREFLIGHT_SCRIPT), str(out_json), str(out_csv)],
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

            if out_json.exists():
                try:
                    with open(out_json, encoding="utf-8") as fh:
                        data = json.load(fh)
                    return PreflightResult.from_dict(data)
                except Exception as exc:
                    log.warning("Failed to parse preflight JSON: %s", exc)

        return self._unavailable("preflight JSON output missing or invalid")

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
