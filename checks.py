"""
checks.py — pre-flight dependency verification.

Checks that the minimum required packages are present and reports
optional tools that improve benchmark quality.  Designed to be
informative, not blocking: missing optional tools are reported but do
not abort the run.
"""

from __future__ import annotations

import importlib.util
import platform
import shutil
import sys
from typing import List, Tuple


# (import_name, display_name, required)
_PYTHON_DEPS: List[Tuple[str, str, bool]] = [
    ("typer",        "typer",          True),
    ("numpy",        "numpy",          False),
    ("torch",        "torch",          False),
    ("onnxruntime",  "onnxruntime",    False),
    ("moderngl",     "moderngl",       False),
]

# (executable_name, display_name, purpose)
_CLI_TOOLS: List[Tuple[str, str, str]] = [
    ("ffmpeg",      "ffmpeg",       "CPU encode benchmark"),
    ("7z",          "7-Zip (7z)",   "CPU compression benchmark"),
    ("nvidia-smi",  "nvidia-smi",   "NVIDIA GPU info"),
]


def verify_deps(verbose: bool = True) -> bool:
    """
    Check dependencies.  Returns True if all *required* packages are present.
    Prints a summary of what was found and what is missing.
    """
    ok = True

    # ── Python packages ────────────────────────────────────────────────
    missing_required: List[str] = []
    missing_optional: List[str] = []

    for import_name, display_name, required in _PYTHON_DEPS:
        found = importlib.util.find_spec(import_name) is not None
        if not found:
            if required:
                missing_required.append(display_name)
            else:
                missing_optional.append(display_name)
        elif verbose:
            print(f"  [OK]  {display_name}")

    if missing_required:
        print(f"[ERROR] Missing required Python packages: {', '.join(missing_required)}")
        print("        Install with:  pip install " + " ".join(missing_required))
        ok = False

    if missing_optional and verbose:
        print(f"[INFO] Optional packages not installed (benchmark quality may be reduced):")
        for p in missing_optional:
            print(f"         pip install {p}")

    # ── CLI tools ──────────────────────────────────────────────────────
    if verbose:
        for exe, name, purpose in _CLI_TOOLS:
            path = shutil.which(exe)
            if path:
                print(f"  [OK]  {name}  ({path})")
            else:
                _hint = _install_hint(exe)
                print(f"  [--]  {name} not found  ({purpose}) — {_hint}")

    if ok and verbose:
        print("[OK] All required dependencies present.")

    return ok


def _install_hint(tool: str) -> str:
    system = platform.system()
    hints = {
        "ffmpeg": {
            "Windows": "winget install Gyan.FFmpeg",
            "Linux":   "sudo apt install ffmpeg",
            "Darwin":  "brew install ffmpeg",
        },
        "7z": {
            "Windows": "winget install 7zip.7zip",
            "Linux":   "sudo apt install 7zip",
            "Darwin":  "brew install p7zip",
        },
    }
    return hints.get(tool, {}).get(system, "install manually")
