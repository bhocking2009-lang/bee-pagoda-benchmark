"""AI benchmark plugin.

Delegates to scripts/bench_ai.sh (llama.cpp + ONNX Runtime + PyTorch).
"""
import os
import subprocess
import tempfile
import json

PLUGIN_ID = "ai"
CATEGORY = "ai"
DEPENDENCIES = []
FALLBACK_CHAIN = ["llama.cpp", "onnxruntime", "torch"]


def run(config: dict) -> dict:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(root, "scripts", "bench_ai.sh")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_json = os.path.join(tmpdir, "ai.json")
        out_csv = os.path.join(tmpdir, "ai.csv")

        env = os.environ.copy()
        for key in ("AI_TIMEOUT_SEC", "AI_MODEL_PATH", "AI_PROMPT_TOKENS", "AI_GEN_TOKENS",
                    "AI_BATCH_SIZE", "AI_CONTEXT_SIZE", "AI_ENABLE_LLAMA",
                    "AI_ENABLE_TORCH", "AI_ENABLE_ONNXRUNTIME",
                    "AI_WEIGHT_LLAMA", "AI_WEIGHT_TORCH", "AI_WEIGHT_ONNXRUNTIME",
                    "AI_REF_LLAMA_TPS", "AI_REF_TORCH_OPS", "AI_REF_ONNXRUNTIME_OPS"):
            if key in config and key not in os.environ:
                env[key] = str(config[key])

        try:
            subprocess.run(["/bin/bash", script, out_json, out_csv], env=env, check=False)
        except Exception as exc:
            return {
                "category": CATEGORY,
                "status": "failed",
                "benchmark": "multi_backend_ai",
                "primary_metric": "composite_normalized",
                "score": None,
                "notes": f"plugin runner error: {exc}",
            }

        if os.path.exists(out_json):
            with open(out_json) as f:
                return json.load(f)

    return {
        "category": CATEGORY,
        "status": "failed",
        "benchmark": "multi_backend_ai",
        "primary_metric": "composite_normalized",
        "score": None,
        "notes": "ai benchmark script produced no output",
    }
