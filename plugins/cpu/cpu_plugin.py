"""CPU benchmark plugin.

Delegates to scripts/bench_cpu.sh and returns a normalized result dict.
"""
import os
import subprocess
import tempfile
import json

PLUGIN_ID = "cpu"
CATEGORY = "cpu"
DEPENDENCIES = ["sysbench", "openssl", "7z", "ffmpeg"]
FALLBACK_CHAIN = ["sysbench", "openssl_speed"]


def run(config: dict) -> dict:
    """Run CPU benchmark suite and return a result dict.

    Parameters
    ----------
    config:
        Profile config mapping (from config_loader.load_config).

    Returns
    -------
    dict
        Benchmark result following the standard schema:
        {category, status, benchmark, primary_metric, score, subtests, notes}
    """
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(root, "scripts", "bench_cpu.sh")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_json = os.path.join(tmpdir, "cpu.json")
        out_csv = os.path.join(tmpdir, "cpu.csv")

        env = os.environ.copy()
        for key in ("CPU_DURATION", "CPU_THREADS", "CPU_COMPRESS_DURATION",
                    "CPU_ENCODE_DURATION", "CPU_STRICT_COMPRESSION"):
            if key in config and key not in os.environ:
                env[key] = str(config[key])

        try:
            subprocess.run(
                ["/bin/bash", script, out_json, out_csv],
                env=env,
                check=False,
            )
        except Exception as exc:
            return {
                "category": CATEGORY,
                "status": "failed",
                "benchmark": "cpu_suite",
                "primary_metric": "baseline_score",
                "score": None,
                "notes": f"plugin runner error: {exc}",
            }

        if os.path.exists(out_json):
            with open(out_json) as f:
                return json.load(f)

    return {
        "category": CATEGORY,
        "status": "failed",
        "benchmark": "cpu_suite",
        "primary_metric": "baseline_score",
        "score": None,
        "notes": "cpu benchmark script produced no output",
    }
