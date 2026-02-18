#!/usr/bin/env bash
set -euo pipefail

OUT_JSON="${1:-/tmp/linux_bench_preflight.json}"
OUT_CSV="${2:-/tmp/linux_bench_preflight.csv}"

PYTHON_BIN="${BENCH_PYTHON:-python3}"

"$PYTHON_BIN" - "$OUT_JSON" "$OUT_CSV" <<'PY'
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

try:
    import importlib.metadata as importlib_metadata
except Exception:
    importlib_metadata = None

out_json, out_csv = sys.argv[1], sys.argv[2]
python_bin = os.environ.get("BENCH_PYTHON") or "python3"

min_python = os.getenv("PREFLIGHT_MIN_PYTHON3", "3.10")
min_pip = os.getenv("PREFLIGHT_MIN_PIP", "23.0")
min_torch = os.getenv("PREFLIGHT_MIN_TORCH", "")
min_onnx = os.getenv("PREFLIGHT_MIN_ONNXRUNTIME", "")


def run_cmd(cmd):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=6)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return 127, str(e)


def extract_version(text):
    m = re.search(r"(\d+(?:\.\d+){0,3})", text)
    return m.group(1) if m else ""


def parse_tuple(v):
    if not v:
        return ()
    parts = re.findall(r"\d+", v)
    return tuple(int(x) for x in parts[:4])


def version_ok(found, minimum):
    if not minimum:
        return True
    f = parse_tuple(found)
    m = parse_tuple(minimum)
    if not f or not m:
        return True
    n = max(len(f), len(m))
    f = f + (0,) * (n - len(f))
    m = m + (0,) * (n - len(m))
    return f >= m


py_rc, py_out = run_cmd([python_bin, "--version"])
python3_version = extract_version(py_out)
python_tuple = parse_tuple(python3_version)


def command_check(name, candidates, required=False, min_version="", version_args=("--version",), notes=""):
    cmd_path = None
    cmd_name = None
    for c in candidates:
        p = shutil.which(c)
        if p:
            cmd_path = p
            cmd_name = c
            break

    if not cmd_path:
        return {
            "name": name,
            "type": "command",
            "required": required,
            "status": "missing" if required else "optional-missing",
            "version": None,
            "min_version": min_version or None,
            "path": None,
            "notes": f"not found in PATH ({', '.join(candidates)})" if not notes else notes,
        }

    rc, out = run_cmd([cmd_name, *version_args])
    if rc != 0 and version_args != ("--version",):
        rc, out = run_cmd([cmd_name, "--version"])

    version = None
    if name == "nvcc":
        m = re.search(r"release\s+(\d+(?:\.\d+){1,3})", out, re.I)
        if not m:
            m = re.search(r"\bV(\d+(?:\.\d+){1,3})\b", out, re.I)
        version = m.group(1) if m else ""
    else:
        version = extract_version(out)

    status = "present"
    if version and min_version and (not version_ok(version, min_version)):
        status = "version-mismatch"
    elif (not version) and min_version:
        status = "version-mismatch"

    return {
        "name": name,
        "type": "command",
        "required": required,
        "status": status,
        "version": version or None,
        "min_version": min_version or None,
        "path": cmd_path,
        "notes": notes,
    }


def python_module_check(name, module, required=False, min_version=""):
    code = (
        "import importlib.util, json; "
        f"spec=importlib.util.find_spec('{module}'); "
        "print(json.dumps({'found': bool(spec), 'origin': getattr(spec, 'origin', None) if spec else None}))"
    )
    rc, out = run_cmd([python_bin, "-c", code])
    found = False
    origin = None
    if rc == 0:
        try:
            data = json.loads(out.strip().splitlines()[-1])
            found = bool(data.get("found"))
            origin = data.get("origin")
        except Exception:
            found = False

    if not found:
        return {
            "name": name,
            "type": "python_module",
            "required": required,
            "status": "missing" if required else "optional-missing",
            "version": None,
            "min_version": min_version or None,
            "path": origin,
            "notes": f"python module '{module}' not importable",
        }

    rc2, out2 = run_cmd([python_bin, "-c", f"import {module}; print(getattr({module}, '__version__', 'unknown'))"])
    version = out2.strip().splitlines()[-1] if rc2 == 0 and out2.strip() else "unknown"
    status = "present"
    if version != "unknown" and min_version and (not version_ok(version, min_version)):
        status = "version-mismatch"
    elif version == "unknown" and min_version:
        status = "version-mismatch"

    return {
        "name": name,
        "type": "python_module",
        "required": required,
        "status": status,
        "version": None if version == "unknown" else version,
        "min_version": min_version or None,
        "path": origin,
        "notes": "",
    }


def pip_check(min_version=""):
    rc, out = run_cmd([python_bin, "-m", "pip", "--version"])
    version = extract_version(out)
    status = "present"
    if rc != 0:
        status = "missing"
    elif min_version and (not version or not version_ok(version, min_version)):
        status = "version-mismatch"
    return {
        "name": "pip",
        "type": "python_module",
        "required": True,
        "status": status,
        "version": version or None,
        "min_version": min_version or None,
        "path": python_bin,
        "notes": "checked via python -m pip",
    }


def has_distribution(dist_name):
    if importlib_metadata is None:
        return False
    try:
        importlib_metadata.version(dist_name)
        return True
    except Exception:
        return False


checks = []

checks.append(command_check("python3", [python_bin], required=True, min_version=min_python, notes="interpreter used by suite"))
checks.append(pip_check(min_version=min_pip))
torch_check = python_module_check("torch", "torch", required=False, min_version=min_torch)
if torch_check["status"] in ("optional-missing", "missing") and python_tuple >= (3, 14):
    msg = "PyTorch wheels are often unavailable on Python 3.14; use Python 3.12/3.13 for torch benchmarks"
    torch_check["notes"] = f"{torch_check.get('notes','')}; {msg}".strip("; ")
checks.append(torch_check)

onnx_check = python_module_check("onnxruntime", "onnxruntime", required=False, min_version=min_onnx)
if has_distribution("onnxruntime-gpu"):
    onnx_check["notes"] = (onnx_check.get("notes") or "") + ("; " if onnx_check.get("notes") else "") + "onnxruntime-gpu distribution detected"
checks.append(onnx_check)

llama = command_check("llama-bench", ["llama-bench", "llama.cpp-bench"], required=False)
if llama["status"] in ("optional-missing", "missing"):
    local_candidates = [
        os.getenv("AI_LLAMA_BENCH_PATH", ""),
        os.path.abspath("./llama.cpp/build/bin/llama-bench"),
        os.path.abspath("./llama.cpp/build/bin/llama.cpp-bench"),
        os.path.abspath("../llama.cpp/build/bin/llama-bench"),
        os.path.abspath("../llama.cpp/build/bin/llama.cpp-bench"),
    ]
    for local_llama in local_candidates:
        if local_llama and os.path.exists(local_llama) and os.access(local_llama, os.X_OK):
            llama["status"] = "present"
            llama["path"] = local_llama
            rc, out = run_cmd([local_llama, "--version"])
            llama["version"] = extract_version(out) or None
            llama["notes"] = f"found local llama-bench binary ({local_llama})"
            break
checks.append(llama)

checks.append(command_check("nvcc", ["nvcc"], required=False))
checks.append(command_check("nvidia-smi", ["nvidia-smi"], required=False))
checks.append(command_check("clpeak", ["clpeak"], required=False))
checks.append(command_check("vkmark", ["vkmark"], required=False))
checks.append(command_check("glmark2", ["glmark2"], required=False))
checks.append(command_check("fio", ["fio"], required=True))
checks.append(command_check("sysbench", ["sysbench"], required=True))
checks.append(command_check("ffmpeg", ["ffmpeg"], required=False, version_args=("-version",)))
checks.append(command_check("7z", ["7z", "7zz"], required=False))
checks.append(command_check("tinymembench", ["tinymembench"], required=False))
checks.append(command_check("hashcat", ["hashcat"], required=False))

counts = {"present": 0, "missing": 0, "version-mismatch": 0, "optional-missing": 0}
for c in checks:
    if c["status"] in counts:
        counts[c["status"]] += 1

if counts["missing"] > 0:
    overall = "failed"
elif counts["version-mismatch"] > 0:
    overall = "degraded"
elif counts["present"] > 0 and counts["optional-missing"] > 0:
    overall = "degraded"
else:
    overall = "ok"

has_nvidia_smi = any(c.get("name") == "nvidia-smi" and c.get("status") == "present" for c in checks)
has_nvcc = any(c.get("name") == "nvcc" and c.get("status") == "present" for c in checks)
has_torch = torch_check.get("status") == "present"
has_onnx = onnx_check.get("status") == "present"
has_onnx_gpu = has_distribution("onnxruntime-gpu")

nvidia_hint = "NVIDIA runtime not detected; CPU AI backends likely only"
if has_nvidia_smi and not has_nvcc:
    nvidia_hint = "NVIDIA driver detected (nvidia-smi present) without CUDA toolkit (nvcc missing)"
elif has_nvidia_smi and has_nvcc:
    nvidia_hint = "NVIDIA driver + CUDA toolkit detected"

ai_dep_hint = "AI optional deps missing: install torch and onnxruntime/onnxruntime-gpu in BENCH_PYTHON env"
if has_torch and has_onnx:
    ai_dep_hint = "AI optional deps present"
elif has_torch and not has_onnx:
    ai_dep_hint = "torch present; install onnxruntime (CPU) or onnxruntime-gpu (NVIDIA)"
elif has_onnx and not has_torch:
    ai_dep_hint = "onnxruntime present; install torch for additional proxy backend"

if has_nvidia_smi and has_onnx and not has_onnx_gpu:
    ai_dep_hint += "; NVIDIA detected but onnxruntime-gpu not installed"

summary = {
    "category": "preflight",
    "status": overall,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "status_counts": counts,
    "checks": checks,
    "interpreter": python_bin,
    "notes": f"Status classes: present, missing, version-mismatch, optional-missing; {nvidia_hint}; {ai_dep_hint}",
}

with open(out_json, "w") as f:
    json.dump(summary, f, indent=2)

with open(out_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["name", "type", "required", "status", "version", "min_version", "path", "notes"])
    for c in checks:
        w.writerow([
            c.get("name"), c.get("type"), c.get("required"), c.get("status"),
            c.get("version") or "", c.get("min_version") or "", c.get("path") or "", c.get("notes") or "",
        ])

print(out_json)
PY
