"""
config_loader.py — loads benchmark profiles.

Profiles are plain KEY=VALUE .env files (see profiles/*.env).
Returns a dict of all settings so callers can use config.get("CPU_DURATION", 60).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict


def load_config(file_path: str) -> Dict[str, Any]:
    """
    Load a profile file.

    Accepts both an explicit path and a bare profile name.
    Resolution order:
      1. The path as given (if it ends with .env)
      2. {path}.env  (e.g. "profiles/balanced" → "profiles/balanced.env")
      3. profiles/{name}.env
    """
    path = Path(file_path)

    # If caller passed "profiles/balanced.yaml" (old style), remap to .env
    if path.suffix in (".yaml", ".yml"):
        path = path.with_suffix(".env")

    if not path.exists():
        # Try adding .env suffix
        candidate = Path(str(path) + ".env")
        if candidate.exists():
            path = candidate

    if not path.exists():
        raise FileNotFoundError(
            f"Profile not found: {path}\n"
            f"Available profiles: {_list_profiles()}"
        )

    return _parse_env_file(path)


def _parse_env_file(path: Path) -> Dict[str, Any]:
    """Parse a KEY=VALUE .env file into a dict."""
    config: Dict[str, Any] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, raw_val = line.partition("=")
                key = key.strip()
                val: Any = raw_val.strip()
                # Try to coerce to int / float
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        pass  # keep as str
                if key:
                    config[key] = val
    return config


def _list_profiles() -> str:
    profiles_dir = Path(__file__).parent / "profiles"
    if profiles_dir.is_dir():
        names = sorted(p.stem for p in profiles_dir.glob("*.env"))
        return ", ".join(names) if names else "(none found)"
    return "(profiles/ directory not found)"
