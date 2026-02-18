#!/usr/bin/env python3
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_nvcc_parse():
    sample = """nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2025 NVIDIA Corporation
Cuda compilation tools, release 12.4, V12.4.131
Build cuda_12.4.r12.4/compiler.34097967_0
"""
    m = re.search(r"release\s+(\d+(?:\.\d+){1,3})", sample, re.I)
    if not m:
        m = re.search(r"\bV(\d+(?:\.\d+){1,3})\b", sample, re.I)
    assert m and m.group(1) == "12.4", f"unexpected nvcc parse: {m.group(1) if m else None}"


def test_llama_discovery_env_override():
    bench_ai = ROOT / "scripts" / "bench_ai.sh"
    with tempfile.TemporaryDirectory() as td:
        fake = Path(td) / "llama-bench"
        fake.write_text("#!/usr/bin/env bash\nexit 1\n")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        env = os.environ.copy()
        env["AI_LLAMA_BENCH_PATH"] = str(fake)
        env["AI_ENABLE_TORCH"] = "0"
        env["AI_ENABLE_ONNXRUNTIME"] = "0"
        env["AI_MODEL_PATH"] = ""
        out_json = Path(td) / "ai.json"
        out_csv = Path(td) / "ai.csv"
        p = subprocess.run([str(bench_ai), str(out_json), str(out_csv)], env=env, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        data = json.loads(out_json.read_text())
        b0 = data.get("backend_results", [{}])[0]
        assert b0.get("backend") == "llama.cpp"
        assert b0.get("data_source") == "real_model"


def test_run_suite_respects_env_toggles_over_profile_defaults():
    run_suite = ROOT / "run_suite.sh"
    with tempfile.TemporaryDirectory() as td:
        env = os.environ.copy()
        env["AI_ENABLE_LLAMA"] = "0"
        env["AI_ENABLE_TORCH"] = "0"
        env["AI_ENABLE_ONNXRUNTIME"] = "0"
        env["BENCH_PYTHON"] = sys.executable
        p = subprocess.run([str(run_suite), "quick", "ai", "--skip-preflight"], cwd=ROOT, env=env, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr

        report_line = next((ln for ln in p.stdout.splitlines() if ln.startswith("[OK] Report: ")), "")
        assert report_line, f"missing report path in output: {p.stdout}"
        report_path = Path(report_line.split(": ", 1)[1].strip())
        ai_json = report_path.parent.parent / "raw" / "ai.json"
        data = json.loads(ai_json.read_text())

        by_backend = {r.get("backend"): r for r in data.get("backend_results", [])}
        for backend, toggle in (("llama.cpp", "AI_ENABLE_LLAMA"), ("onnxruntime", "AI_ENABLE_ONNXRUNTIME"), ("torch", "AI_ENABLE_TORCH")):
            item = by_backend.get(backend)
            assert item is not None, f"missing backend result: {backend}"
            assert item.get("status") == "skipped", f"{backend} status was {item.get('status')}"
            assert item.get("disabled") is True, f"{backend} disabled flag missing"
            assert item.get("disabled_by") == toggle, f"{backend} disabled_by mismatch: {item.get('disabled_by')}"
            assert f"disabled by {toggle}=0" in (item.get("notes") or ""), f"{backend} notes missing disable reason"


def main():
    test_nvcc_parse()
    test_llama_discovery_env_override()
    test_run_suite_respects_env_toggles_over_profile_defaults()
    print("validate_fixes.py: OK")


if __name__ == "__main__":
    main()
