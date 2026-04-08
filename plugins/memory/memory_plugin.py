"""Memory benchmark plugin.

Delegates to scripts/bench_memory.sh (sysbench memory + tinymembench).
"""
import os
import subprocess
import tempfile
import json

PLUGIN_ID = "memory"
CATEGORY = "memory"
DEPENDENCIES = ["sysbench", "tinymembench"]
FALLBACK_CHAIN = ["sysbench_memory", "tinymembench"]


def run(config: dict) -> dict:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(root, "scripts", "bench_memory.sh")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_json = os.path.join(tmpdir, "memory.json")
        out_csv = os.path.join(tmpdir, "memory.csv")

        env = os.environ.copy()
        for key in ("MEMORY_THREADS", "MEMORY_BLOCK_SIZE", "MEMORY_TOTAL_SIZE"):
            if key in config and key not in os.environ:
                env[key] = str(config[key])

        try:
            subprocess.run(["/bin/bash", script, out_json, out_csv], env=env, check=False)
        except Exception as exc:
            return {
                "category": CATEGORY,
                "status": "failed",
                "benchmark": "memory_suite",
                "primary_metric": "read_write_mib_per_sec",
                "score": None,
                "notes": f"plugin runner error: {exc}",
            }

        if os.path.exists(out_json):
            with open(out_json) as f:
                return json.load(f)

    return {
        "category": CATEGORY,
        "status": "failed",
        "benchmark": "memory_suite",
        "primary_metric": "read_write_mib_per_sec",
        "score": None,
        "notes": "memory benchmark script produced no output",
    }
