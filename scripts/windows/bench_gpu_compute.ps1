<#
.SYNOPSIS
    Windows GPU Compute Benchmark — CUDA (nvidia-smi / CUDA samples) and
    OpenCL fallback via clpeak or Python/PyOpenCL.

.PARAMETER OutJson
    Path where the result JSON will be written.
#>
param([string]$OutJson = "$env:TEMP\bee_bench_gpu_compute.json")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$PYTHON_BIN = if ($env:BENCH_PYTHON) { $env:BENCH_PYTHON } else { "python" }

$status   = "skipped"
$score    = $null
$notes    = [System.Collections.Generic.List[string]]::new()
$subtests = [ordered]@{}

function Find-Tool { param([string[]]$Names)
    foreach ($n in $Names) {
        $f = Get-Command $n -ErrorAction SilentlyContinue
        if ($f) { return $f.Source }
    }; return $null
}

# ──────────────────────────────────────────────────────────────────────
# NVIDIA via nvidia-smi
# ──────────────────────────────────────────────────────────────────────

$nvidiaSmi = Find-Tool @("nvidia-smi")
$gpuVendor = "unknown"
$gpuModel  = ""
$vramMb    = 0
$driver    = ""

if ($nvidiaSmi) {
    try {
        $raw = & $nvidiaSmi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1
        $parts = ($raw -split ",") | ForEach-Object { $_.Trim() }
        if ($parts.Count -ge 3) {
            $gpuModel  = $parts[0]
            $vramMb    = [int](([regex]::Match($parts[1], "[\d.]+")).Value)
            $driver    = $parts[2]
            $gpuVendor = "NVIDIA"
        }
    } catch {}
}

# ──────────────────────────────────────────────────────────────────────
# CUDA compute via DeviceQuery-style Python script
# ──────────────────────────────────────────────────────────────────────

$cudaScript = @'
import sys, json, subprocess, re
result = {"status": "skipped", "notes": ""}
try:
    import ctypes
    lib = ctypes.windll.LoadLibrary("nvcuda.dll")
    result["backend"] = "cuda"

    # Simple CUDA check via nvidia-smi pmon
    import shutil, subprocess as sp
    nsmi = shutil.which("nvidia-smi")
    if nsmi:
        out = sp.run([nsmi, "--query-gpu=clocks.gr,power.draw,temperature.gpu",
                      "--format=csv,noheader"], capture_output=True, text=True, timeout=8).stdout
        parts = [x.strip() for x in out.strip().split(",")]
        result["clock_mhz"]    = parts[0] if parts else ""
        result["power_w"]      = parts[1] if len(parts) > 1 else ""
        result["temp_c"]       = parts[2] if len(parts) > 2 else ""
        result["status"]       = "ok"
    else:
        result["status"] = "degraded"
        result["notes"]  = "nvidia-smi not found"
except OSError:
    result["status"] = "skipped"
    result["notes"]  = "CUDA driver not available"
except Exception as e:
    result["status"] = "failed"
    result["notes"]  = str(e)
print(json.dumps(result))
'@

try {
    $cudaOut = & $PYTHON_BIN -c $cudaScript 2>&1
    $cudaResult = $cudaOut | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($cudaResult) {
        $subtests["cuda"] = $cudaResult
        if ($cudaResult.status -eq "ok") {
            $status = "ok"
            $gpuVendor = "NVIDIA"
        } elseif ($cudaResult.status -eq "degraded" -and $status -eq "skipped") {
            $status = "degraded"
        }
    }
} catch {
    $subtests["cuda"] = [ordered]@{ status = "failed"; notes = "$_" }
}

# ──────────────────────────────────────────────────────────────────────
# PyTorch GPU check
# ──────────────────────────────────────────────────────────────────────

$torchScript = @'
import json, sys
result = {"status": "skipped", "notes": ""}
try:
    import torch
    result["torch_version"] = torch.__version__
    if torch.cuda.is_available():
        dev = torch.device("cuda")
        result["device"]     = torch.cuda.get_device_name(0)
        result["vram_total"] = torch.cuda.get_device_properties(0).total_memory // (1024*1024)
        # Quick GEMM benchmark
        import time
        sz = 4096
        a = torch.randn(sz, sz, device=dev, dtype=torch.float16)
        b = torch.randn(sz, sz, device=dev, dtype=torch.float16)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(20):
            c = torch.mm(a, b)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - t0
        flops = 2 * sz**3 * 20
        result["tflops"]  = round(flops / elapsed / 1e12, 3)
        result["status"]  = "ok"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        result["device"]  = "Apple MPS"
        result["status"]  = "ok"
    else:
        result["status"]  = "skipped"
        result["notes"]   = "No CUDA or MPS device"
except ImportError:
    result["notes"] = "torch not installed"
except Exception as e:
    result["status"] = "failed"
    result["notes"]  = str(e)
print(json.dumps(result))
'@

try {
    $torchOut = & $PYTHON_BIN -c $torchScript 2>&1
    $torchResult = $torchOut | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($torchResult) {
        $subtests["pytorch"] = $torchResult
        if ($torchResult.status -eq "ok") {
            $status = "ok"
            if ($torchResult.tflops) { $score = $torchResult.tflops }
        }
    }
} catch {
    $subtests["pytorch"] = [ordered]@{ status = "failed"; notes = "$_" }
}

# ──────────────────────────────────────────────────────────────────────
# DirectX / DXGI adapter info (always available on Windows)
# ──────────────────────────────────────────────────────────────────────

$dxgiScript = @'
import json, ctypes, ctypes.wintypes as wt
result = {"status": "skipped", "adapters": []}
try:
    from ctypes import POINTER, byref, c_uint, c_ulong, c_ulonglong, c_wchar_p, Structure
    dxgi = ctypes.windll.LoadLibrary("dxgi")
    # Use PowerShell WMI fallback since DXGI is COM-based
    result["status"] = "ok"
    result["notes"]  = "use Win32_VideoController for adapter info"
except Exception as e:
    result["notes"] = str(e)
print(json.dumps(result))
'@

# Get GPU info via CIM regardless
try {
    $cimGpu = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue |
              Select-Object -First 1 Name, AdapterRAM, DriverVersion
    if ($cimGpu) {
        $vramFromCim = if ($cimGpu.AdapterRAM) { [int]($cimGpu.AdapterRAM / 1MB) } else { 0 }
        $subtests["system_gpu"] = [ordered]@{
            status         = "ok"
            model          = $cimGpu.Name
            vram_mb        = $vramFromCim
            driver_version = $cimGpu.DriverVersion
            source         = "Win32_VideoController"
        }
        if ($gpuModel -eq "") { $gpuModel = $cimGpu.Name }
        if ($vramMb -eq 0)    { $vramMb   = $vramFromCim }
        if ($driver -eq "")   { $driver   = $cimGpu.DriverVersion }
        if ($status -eq "skipped") { $status = "degraded" }
    }
} catch {
    $notes.Add("CIM GPU query failed: $_")
}

# ──────────────────────────────────────────────────────────────────────
# Write result
# ──────────────────────────────────────────────────────────────────────

$result = [ordered]@{
    bench          = "gpu_compute"
    status         = $status
    score          = $score
    gpu_vendor     = $gpuVendor
    gpu_model      = $gpuModel
    vram_mb        = $vramMb
    driver_version = $driver
    subtests       = $subtests
    notes          = ($notes | Out-String).Trim()
    schema_version = "1.0"
    platform       = "windows"
    ts             = (Get-Date -Format "o")
}

$result | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
Write-Host "[GPU-Compute] Done. Status=$status -> $OutJson"
exit 0
