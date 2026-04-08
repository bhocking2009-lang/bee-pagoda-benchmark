import os
import re


def load_config(file_path: str) -> dict:
    """Load a profile config file.

    Supports both ``.env`` (KEY=VALUE) files (used by ``run_suite.sh``) and
    ``.yaml`` / ``.yml`` files.  Falls back to ``.env`` extension when the
    supplied path does not exist but a same-named ``.env`` variant does.
    """
    # Prefer existing file; fall back to .env variant so callers can pass
    # either "profiles/balanced.yaml" or "profiles/balanced.env".
    if not os.path.exists(file_path):
        base, _ = os.path.splitext(file_path)
        env_path = base + ".env"
        if os.path.exists(env_path):
            file_path = env_path

    _, ext = os.path.splitext(file_path)
    if ext in (".yaml", ".yml"):
        try:
            import yaml
            with open(file_path, "r") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            raise ImportError("pyyaml is required to load YAML profile files. "
                              "Install with: pip install pyyaml")

    # Parse .env KEY=VALUE format
    config: dict = {}
    with open(file_path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line)
            if m:
                key, val = m.group(1), m.group(2).strip()
                # Convert numeric values for convenience
                if re.match(r'^-?[0-9]+$', val):
                    config[key] = int(val)
                elif re.match(r'^-?[0-9]*\.[0-9]+$', val):
                    config[key] = float(val)
                else:
                    config[key] = val
    return config
