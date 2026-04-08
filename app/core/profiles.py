"""
Load .env profile files and expose typed profile objects.

Profiles are plain KEY=VALUE files (no shell quoting, no eval).
The loader never executes any code from the profile file.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

_PROFILES_DIR = Path(__file__).parent.parent.parent / "profiles"

_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


@dataclass
class Profile:
    name: str
    params: Dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Typed accessors for common profile parameters
    # ------------------------------------------------------------------

    def get_int(self, key: str, default: int = 0) -> int:
        v = self.params.get(key, "")
        try:
            return int(v)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        v = self.params.get(key, "")
        try:
            return float(v)
        except (ValueError, TypeError):
            return default

    def get_str(self, key: str, default: str = "") -> str:
        return self.params.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        v = self.params.get(key, "")
        if v.lower() in ("1", "true", "yes"):
            return True
        if v.lower() in ("0", "false", "no"):
            return False
        return default

    # Convenience properties
    @property
    def run_repetitions(self) -> int:
        return max(1, self.get_int("RUN_REPETITIONS", 1))

    @property
    def cpu_duration(self) -> int:
        return self.get_int("CPU_DURATION", 60)

    @property
    def gpu_compute_duration(self) -> int:
        return self.get_int("GPU_COMPUTE_DURATION", 60)

    @property
    def gpu_game_duration(self) -> int:
        return self.get_int("GPU_GAME_DURATION", 60)

    @property
    def ai_timeout(self) -> int:
        return self.get_int("AI_TIMEOUT_SEC", 300)

    @property
    def memory_total_size(self) -> str:
        return self.get_str("MEMORY_TOTAL_SIZE", "8G")

    @property
    def storage_test_size(self) -> str:
        return self.get_str("STORAGE_TEST_SIZE", "512M")


def load_profile(
    profile_name: str,
    profiles_dir: Optional[Path] = None,
) -> Profile:
    """Load and parse a .env profile file."""
    base = profiles_dir or _PROFILES_DIR
    path = Path(base) / f"{profile_name}.env"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")

    params: Dict[str, str] = {}
    with open(path, encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            m = _KEY_RE.match(line)
            if m:
                params[m.group(1)] = m.group(2).strip()
            else:
                log.debug("Skipping unrecognised profile line: %r", line)

    log.debug("Loaded profile %r (%d params) from %s", profile_name, len(params), path)
    return Profile(name=profile_name, params=params)


def list_profiles(profiles_dir: Optional[Path] = None) -> List[str]:
    """Return all available profile names (without extension)."""
    base = profiles_dir or _PROFILES_DIR
    base = Path(base)
    if not base.is_dir():
        return []
    return sorted(p.stem for p in base.glob("*.env"))
