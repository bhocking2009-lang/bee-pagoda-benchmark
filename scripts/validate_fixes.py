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


def _write_executable(path: Path, content: str):
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


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


def test_cpu_encode_fallback_uses_devnull_target_and_degrades():
    bench_cpu = ROOT / "scripts" / "bench_cpu.sh"
    with tempfile.TemporaryDirectory() as td:
        bindir = Path(td) / "bin"
        bindir.mkdir()

        _write_executable(bindir / "sysbench", "#!/usr/bin/env bash\necho 'events per second: 123.45'\n")
        _write_executable(bindir / "7z", "#!/usr/bin/env bash\necho 'Tot: 9999 MIPS'\n")
        _write_executable(
            bindir / "timeout",
            "#!/usr/bin/env bash\n"
            "if [[ \"${1:-}\" == \"--foreground\" ]]; then shift; fi\n"
            "shift\n"
            "exec \"$@\"\n",
        )
        _write_executable(
            bindir / "ffmpeg",
            "#!/usr/bin/env bash\n"
            "if [[ \"${1:-}\" == \"-version\" ]]; then\n"
            "  echo 'ffmpeg version n7-test'\n"
            "  exit 0\n"
            "fi\n"
            "printf '%s\\n' \"$@\" > \"${TMP_FFMPEG_ARGS:?}\"\n"
            "case \" $* \" in *\" -c:v libx264 \"*) exit 1 ;; esac\n"
            "case \" $* \" in *\" -c:v mpeg4 \"*) exit 0 ;; esac\n"
            "exit 2\n",
        )

        out_json = Path(td) / "cpu.json"
        out_csv = Path(td) / "cpu.csv"
        args_file = Path(td) / "ffmpeg.args"

        env = os.environ.copy()
        env["PATH"] = f"{bindir}:{env.get('PATH', '')}"
        env["TMP_FFMPEG_ARGS"] = str(args_file)
        env["CPU_DURATION"] = "1"
        env["CPU_COMPRESS_DURATION"] = "1"
        env["CPU_ENCODE_DURATION"] = "1"

        p = subprocess.run([str(bench_cpu), str(out_json), str(out_csv)], cwd=ROOT, env=env, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr

        data = json.loads(out_json.read_text())
        assert data["subtests"]["encoding"]["status"] == "degraded"
        assert data["subtests"]["encoding"]["tool"] == "ffmpeg_mpeg4"
        assert data["diagnostics"]["ffmpeg"]["output_target"] == "/dev/null"
        assert data["diagnostics"]["ffmpeg"]["timeout_wrapper"] == "timeout"

        args = args_file.read_text()
        assert "/dev/null" in args, args


def test_cpu_encode_failure_includes_explicit_diagnostics_when_stderr_empty():
    bench_cpu = ROOT / "scripts" / "bench_cpu.sh"
    with tempfile.TemporaryDirectory() as td:
        bindir = Path(td) / "bin"
        bindir.mkdir()

        _write_executable(
            bindir / "ffmpeg",
            "#!/usr/bin/env bash\n"
            "if [[ \"${1:-}\" == \"-version\" ]]; then\n"
            "  echo 'ffmpeg version n7-test'\n"
            "  exit 0\n"
            "fi\n"
            "exit 42\n",
        )

        out_json = Path(td) / "cpu.json"
        out_csv = Path(td) / "cpu.csv"

        env = os.environ.copy()
        env["PATH"] = f"{bindir}:{env.get('PATH', '')}"
        env["CPU_DURATION"] = "1"
        env["CPU_COMPRESS_DURATION"] = "1"
        env["CPU_ENCODE_DURATION"] = "1"

        p = subprocess.run([str(bench_cpu), str(out_json), str(out_csv)], cwd=ROOT, env=env, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr

        data = json.loads(out_json.read_text())
        notes = data.get("notes", "")
        ffdiag = data["diagnostics"]["ffmpeg"]

        assert data["subtests"]["encoding"]["status"] == "failed"
        assert ffdiag["error_code"] == "42"
        assert ffdiag["error_reason"] == "exit_42"
        assert ffdiag["error_tail"] == "no_stderr_output"
        assert "encoding_ffmpeg_fallback_failed:exit_42:no_stderr_output" in notes


def main():
    test_nvcc_parse()
    test_llama_discovery_env_override()
    test_run_suite_respects_env_toggles_over_profile_defaults()
    test_cpu_encode_fallback_uses_devnull_target_and_degrades()
    test_cpu_encode_failure_includes_explicit_diagnostics_when_stderr_empty()
    print("validate_fixes.py: OK")


if __name__ == "__main__":
    main()
