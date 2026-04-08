"""GPU compute benchmark plugin.

Delegates to scripts/bench_gpu_compute.sh.
"""
import os
import subprocess
import tempfile
import json

PLUGIN_ID = "gpu_compute"
CATEGORY = "gpu_compute"
DEPENDENCIES = ["clpeak", "hashcat"]
FALLBACK_CHAIN = ["clpeak", "hashcat"]


def run(config: dict) -> dict:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(root, "scripts", "bench_gpu_compute.sh")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_json = os.path.join(tmpdir, "gpu_compute.json")
        out_csv = os.path.join(tmpdir, "gpu_compute.csv")

        env = os.environ.copy()
        for key in ("GPU_COMPUTE_DURATION", "GPU_COMPUTE_TIMEOUT_SEC"):
            if key in config and key not in os.environ:
                env[key] = str(config[key])

        try:
            subprocess.run(["/bin/bash", script, out_json, out_csv], env=env, check=False)
        except Exception as exc:
            return {
                "category": CATEGORY,
                "status": "failed",
                "benchmark": "none",
                "primary_metric": "score",
                "score": None,
                "notes": f"plugin runner error: {exc}",
            }

        if os.path.exists(out_json):
            with open(out_json) as f:
                return json.load(f)

    return {
        "category": CATEGORY,
        "status": "failed",
        "benchmark": "none",
        "primary_metric": "score",
        "score": None,
        "notes": "gpu_compute benchmark script produced no output",
    }
