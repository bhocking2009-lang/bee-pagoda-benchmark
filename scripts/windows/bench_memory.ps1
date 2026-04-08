<#
.SYNOPSIS
    Windows Memory Benchmark — bandwidth and latency via Python.

.PARAMETER OutJson
    Path where the result JSON will be written.
#>
param([string]$OutJson = "$env:TEMP\bee_bench_memory.json")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$PYTHON_BIN = if ($env:BENCH_PYTHON) { $env:BENCH_PYTHON } else { "python" }
$DURATION   = if ($env:MEM_DURATION)  { [int]$env:MEM_DURATION } else { 10 }

$status   = "ok"
$notes    = [System.Collections.Generic.List[string]]::new()
$subtests = [ordered]@{}

# ──────────────────────────────────────────────────────────────────────
# System memory info via WMI
# ──────────────────────────────────────────────────────────────────────

try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
    if ($os) {
        $subtests["system_ram"] = [ordered]@{
            status       = "ok"
            total_mb     = [int]($os.TotalVisibleMemorySize / 1024)
            available_mb = [int]($os.FreePhysicalMemory / 1024)
        }
    }
    # Memory speed from Win32_PhysicalMemory
    $dimms = Get-CimInstance Win32_PhysicalMemory -ErrorAction SilentlyContinue
    if ($dimms) {
        $speeds = $dimms | Where-Object { $_.Speed } | Select-Object -ExpandProperty Speed
        if ($speeds) {
            $subtests["dimm_speed_mhz"] = [ordered]@{
                status   = "ok"
                speed_mhz = ($speeds | Measure-Object -Maximum).Maximum
                channels  = ($dimms | Measure-Object).Count
            }
        }
    }
} catch {
    $notes.Add("WMI memory query failed: $_")
}

# ──────────────────────────────────────────────────────────────────────
# Bandwidth benchmark via Python (numpy memcpy equivalent)
# ──────────────────────────────────────────────────────────────────────

$bwScript = @"
import json, time, sys
result = {"status": "skipped", "notes": ""}
DURATION = $DURATION
try:
    import numpy as np
    # Sequential read bandwidth
    SIZE_MB = 512
    arr = np.random.randn(SIZE_MB * 1024 * 1024 // 8).astype(np.float64)
    ITERS = max(1, int(DURATION / 2))
    t0 = time.perf_counter()
    for _ in range(ITERS):
        s = arr.sum()
    elapsed = time.perf_counter() - t0
    read_bw_gbps = round(SIZE_MB * ITERS / elapsed / 1024, 3)

    # Sequential write bandwidth
    dst = np.empty_like(arr)
    t0 = time.perf_counter()
    for _ in range(ITERS):
        np.copyto(dst, arr)
    elapsed = time.perf_counter() - t0
    write_bw_gbps = round(SIZE_MB * ITERS / elapsed / 1024, 3)

    result["status"]         = "ok"
    result["read_gbps"]      = read_bw_gbps
    result["write_gbps"]     = write_bw_gbps
    result["buffer_size_mb"] = SIZE_MB
    result["backend"]        = "numpy"
except ImportError:
    result["notes"] = "numpy not installed"
except Exception as e:
    result["status"] = "failed"
    result["notes"]  = str(e)
print(json.dumps(result))
"@

try {
    $bwOut = & $PYTHON_BIN -c $bwScript 2>&1
    $bwResult = $bwOut | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($bwResult) {
        $subtests["bandwidth"] = $bwResult
        if ($bwResult.status -ne "ok") {
            $status = "degraded"
            $notes.Add("Bandwidth benchmark: $($bwResult.notes)")
        }
    }
} catch {
    $subtests["bandwidth"] = [ordered]@{ status = "failed"; notes = "$_" }
    $status = "degraded"
}

# ──────────────────────────────────────────────────────────────────────
# Latency benchmark via Python pointer-chase
# ──────────────────────────────────────────────────────────────────────

$latScript = @'
import json, time, random, array
result = {"status": "skipped", "notes": ""}
try:
    SIZE = 64 * 1024 * 1024 // 8   # 64 MB in 8-byte slots
    buf = list(range(SIZE))
    random.shuffle(buf)
    idx = buf[0]
    STEPS = 5_000_000
    t0 = time.perf_counter()
    for _ in range(STEPS):
        idx = buf[idx % SIZE]
    elapsed = time.perf_counter() - t0
    latency_ns = elapsed / STEPS * 1e9
    result["status"]     = "ok"
    result["latency_ns"] = round(latency_ns, 2)
    result["backend"]    = "python_chase"
except Exception as e:
    result["status"] = "failed"
    result["notes"]  = str(e)
print(json.dumps(result))
'@

try {
    $latOut = & $PYTHON_BIN -c $latScript 2>&1
    $latResult = $latOut | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($latResult) { $subtests["latency"] = $latResult }
} catch {
    $subtests["latency"] = [ordered]@{ status = "failed"; notes = "$_" }
}

# Score: read bandwidth in GB/s
$score = if ($subtests["bandwidth"] -and $subtests["bandwidth"].read_gbps) {
    $subtests["bandwidth"].read_gbps
} else { $null }

# ──────────────────────────────────────────────────────────────────────
# Write result
# ──────────────────────────────────────────────────────────────────────

$result = [ordered]@{
    bench          = "memory"
    status         = $status
    score          = $score
    subtests       = $subtests
    notes          = ($notes | Out-String).Trim()
    schema_version = "1.0"
    platform       = "windows"
    ts             = (Get-Date -Format "o")
}

$result | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
Write-Host "[Memory] Done. Status=$status Score=$score -> $OutJson"
exit 0
