"""Disk/Storage benchmark plugin.

Delegates to scripts/bench_storage.sh (fio sequential + random).
"""
import os
import subprocess
import tempfile
import json

PLUGIN_ID = "disk"
CATEGORY = "disk"
DEPENDENCIES = ["fio"]
FALLBACK_CHAIN = ["fio"]


def run(config: dict) -> dict:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(root, "scripts", "bench_storage.sh")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_json = os.path.join(tmpdir, "disk.json")
        out_csv = os.path.join(tmpdir, "disk.csv")

        env = os.environ.copy()
        env.setdefault("STORAGE_WORKDIR", tmpdir)
        for key in ("STORAGE_TEST_SIZE", "STORAGE_RUNTIME"):
            if key in config and key not in os.environ:
                env[key] = str(config[key])

        try:
            subprocess.run(["/bin/bash", script, out_json, out_csv], env=env, check=False)
        except Exception as exc:
            return {
                "category": CATEGORY,
                "status": "failed",
                "benchmark": "fio_file_safe",
                "primary_metric": "seq_bw_kib_per_sec",
                "score": None,
                "notes": f"plugin runner error: {exc}",
            }

        if os.path.exists(out_json):
            with open(out_json) as f:
                return json.load(f)

    return {
        "category": CATEGORY,
        "status": "failed",
        "benchmark": "fio_file_safe",
        "primary_metric": "seq_bw_kib_per_sec",
        "score": None,
        "notes": "disk benchmark script produced no output",
    }
