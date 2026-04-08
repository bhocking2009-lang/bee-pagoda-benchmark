<#
.SYNOPSIS
    Windows CPU Benchmark — 7-Zip compression throughput + ffmpeg encode.

.PARAMETER OutJson
    Path where the result JSON will be written.
#>
param([string]$OutJson = "$env:TEMP\bee_bench_cpu.json")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$PYTHON_BIN = if ($env:BENCH_PYTHON) { $env:BENCH_PYTHON } else { "python" }
$DURATION   = if ($env:CPU_DURATION)  { [int]$env:CPU_DURATION  } else { 60 }
$THREADS    = if ($env:CPU_THREADS -and $env:CPU_THREADS -ne "0") {
                  [int]$env:CPU_THREADS
              } else {
                  [Environment]::ProcessorCount
              }

$status       = "ok"
$score        = $null
$notes        = [System.Collections.Generic.List[string]]::new()
$subtests     = [ordered]@{}
$bench        = "cpu_suite"

# ──────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────

function Find-Tool {
    param([string[]]$Names)
    foreach ($name in $Names) {
        $found = Get-Command $name -ErrorAction SilentlyContinue
        if ($found) { return $found.Source }
    }
    return $null
}

function Invoke-TimedCommand {
    param([string]$Label, [scriptblock]$Block)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $result = & $Block
    $sw.Stop()
    return @{ output = $result; elapsed_s = [math]::Round($sw.Elapsed.TotalSeconds, 3) }
}

# ──────────────────────────────────────────────────────────────────────
# 7-Zip compression benchmark
# ──────────────────────────────────────────────────────────────────────

$sevenzip = Find-Tool @("7z", "7za", "7zr")
$compressStatus = "skipped"
$compressTool   = "none"
$compressScore  = $null

if ($sevenzip) {
    Write-Host "[CPU] Running 7-Zip benchmark ($THREADS threads, ${DURATION}s)..."
    try {
        $res = Invoke-TimedCommand -Label "7z_bench" -Block {
            # 7-Zip built-in benchmark
            & $sevenzip b -mmt=$THREADS 2>&1
        }
        $output = $res.output -join "`n"
        # Parse "Tot:   <compress MIPS>   <decompress MIPS>"
        $totLine = $output | Select-String "Tot:" | Select-Object -Last 1
        if ($totLine) {
            $parts = ($totLine -split '\s+') | Where-Object { $_ -ne "" }
            if ($parts.Count -ge 3) {
                $compressScore = [double]$parts[1]
                $compressStatus = "ok"
                $score = $compressScore
            }
        }
        $compressTool = $sevenzip
        $subtests["compress"] = [ordered]@{
            status    = $compressStatus
            tool      = $compressTool
            score_mips = $compressScore
            elapsed_s  = $res.elapsed_s
            notes      = ""
        }
    } catch {
        $compressStatus = "failed"
        $notes.Add("7z benchmark failed: $_")
        $subtests["compress"] = [ordered]@{
            status = "failed"
            tool   = $sevenzip
            notes  = "$_"
        }
    }
} else {
    $notes.Add("7z/7za not found; install 7-Zip for compression benchmark")
    $subtests["compress"] = [ordered]@{
        status = "skipped"
        tool   = "none"
        notes  = "7z not found"
    }
}

# ──────────────────────────────────────────────────────────────────────
# ffmpeg encode benchmark
# ──────────────────────────────────────────────────────────────────────

$ffmpeg = Find-Tool @("ffmpeg")
$encodeStatus = "skipped"
$encodeTool   = "none"
$encodeFps    = $null

if ($ffmpeg) {
    Write-Host "[CPU] Running ffmpeg encode benchmark (${DURATION}s)..."
    try {
        $tmpOut = Join-Path $env:TEMP "bee_cpu_encode_out.mp4"
        $res = Invoke-TimedCommand -Label "ffmpeg_encode" -Block {
            & $ffmpeg -y -f lavfi -i "testsrc=duration=${DURATION}:size=1280x720:rate=30" `
                -c:v libx264 -preset medium -crf 23 -t $DURATION `
                -threads $THREADS NUL 2>&1
        }
        $output = $res.output -join "`n"
        # Parse "fps=  XX"
        $fpsMatch = [regex]::Match($output, "fps=\s*([\d.]+)")
        if ($fpsMatch.Success) {
            $encodeFps    = [double]$fpsMatch.Groups[1].Value
            $encodeStatus = "ok"
        } else {
            $encodeStatus = "degraded"
            $notes.Add("ffmpeg encode ran but fps could not be parsed")
        }
        $encodeTool = $ffmpeg
        $subtests["encode"] = [ordered]@{
            status     = $encodeStatus
            tool       = $encodeTool
            fps        = $encodeFps
            elapsed_s  = $res.elapsed_s
            notes      = ""
        }
    } catch {
        $encodeStatus = "failed"
        $notes.Add("ffmpeg encode failed: $_")
        $subtests["encode"] = [ordered]@{
            status = "failed"
            tool   = "ffmpeg"
            notes  = "$_"
        }
    }
} else {
    $notes.Add("ffmpeg not found; install ffmpeg for encode benchmark")
    $subtests["encode"] = [ordered]@{
        status = "skipped"
        tool   = "none"
        notes  = "ffmpeg not found"
    }
}

# ──────────────────────────────────────────────────────────────────────
# Python math fallback (always runs as a baseline)
# ──────────────────────────────────────────────────────────────────────

Write-Host "[CPU] Running Python math baseline..."
$pyResult = $null
try {
    $pyScript = @"
import time, math, sys
t0 = time.perf_counter()
n = 0
while time.perf_counter() - t0 < 5:
    x = sum(math.sqrt(i) for i in range(1, 100001))
    n += 1
elapsed = time.perf_counter() - t0
ops_per_sec = n * 100000 / elapsed
print(f"{ops_per_sec:.0f}")
"@
    $pyRes = Invoke-TimedCommand -Label "py_math" -Block {
        & $PYTHON_BIN -c $pyScript 2>&1
    }
    $opsPerSec = ($pyRes.output -join "").Trim()
    $pyResult = [ordered]@{
        status       = "ok"
        tool         = $PYTHON_BIN
        ops_per_sec  = [double]$opsPerSec
        elapsed_s    = $pyRes.elapsed_s
        notes        = "Python math baseline (5s)"
    }
    if ($null -eq $score) {
        $score  = [double]$opsPerSec / 1000000.0
        $status = "degraded"
        $notes.Add("Primary tools unavailable; using Python math baseline")
    }
} catch {
    $pyResult = [ordered]@{
        status = "failed"
        notes  = "$_"
    }
}
$subtests["python_baseline"] = $pyResult

# Determine overall status
if ($compressStatus -eq "failed" -and $encodeStatus -eq "failed") {
    $status = "degraded"
}
if ($compressStatus -eq "ok" -or $encodeStatus -eq "ok") {
    $status = "ok"
}

# ──────────────────────────────────────────────────────────────────────
# Write result
# ──────────────────────────────────────────────────────────────────────

$result = [ordered]@{
    bench    = $bench
    status   = $status
    score    = $score
    threads  = $THREADS
    duration = $DURATION
    subtests = $subtests
    notes    = ($notes | Out-String).Trim()
    schema_version = "1.0"
    platform = "windows"
    ts       = (Get-Date -Format "o")
}

$result | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
Write-Host "[CPU] Done. Status=$status Score=$score -> $OutJson"
exit 0
