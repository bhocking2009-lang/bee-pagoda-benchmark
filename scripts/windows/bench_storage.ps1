<#
.SYNOPSIS
    Windows Storage Benchmark — sequential read/write and IOPS via Python,
    with CrystalDiskMark-style workload. Avoids destructive raw-device access.

.PARAMETER OutJson
    Path where the result JSON will be written.
#>
param([string]$OutJson = "$env:TEMP\bee_bench_storage.json")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$PYTHON_BIN  = if ($env:BENCH_PYTHON)      { $env:BENCH_PYTHON     } else { "python" }
$TEST_DIR    = if ($env:DISK_TEST_DIR)     { $env:DISK_TEST_DIR    } else { $env:TEMP }
$FILE_SIZE   = if ($env:DISK_FILE_SIZE_MB) { [int]$env:DISK_FILE_SIZE_MB } else { 512 }
$DURATION    = if ($env:DISK_DURATION)     { [int]$env:DISK_DURATION     } else { 10  }

$status   = "ok"
$notes    = [System.Collections.Generic.List[string]]::new()
$subtests = [ordered]@{}

# ──────────────────────────────────────────────────────────────────────
# Disk info via WMI
# ──────────────────────────────────────────────────────────────────────

try {
    $drive = (Split-Path -Qualifier $TEST_DIR).TrimEnd("\")
    $disk  = Get-PSDrive -Name $drive.TrimEnd(":") -ErrorAction SilentlyContinue
    if ($disk) {
        $usedGB = [math]::Round($disk.Used / 1GB, 2)
        $freeGB = [math]::Round($disk.Free / 1GB, 2)
        $subtests["drive_info"] = [ordered]@{
            status   = "ok"
            drive    = $drive
            used_gb  = $usedGB
            free_gb  = $freeGB
        }
    }

    # Disk type
    $partition = Get-Partition -DriveLetter $drive.TrimEnd(":") -ErrorAction SilentlyContinue
    if ($partition) {
        $diskObj = $partition | Get-Disk -ErrorAction SilentlyContinue
        if ($diskObj) {
            $diskType = $diskObj.MediaType  # "SSD", "HDD", "Unspecified"
            if ($subtests["drive_info"]) {
                $subtests["drive_info"]["type"] = $diskType
            }
        }
    }
} catch {
    $notes.Add("Disk info query failed: $_")
}

# ──────────────────────────────────────────────────────────────────────
# Sequential read/write benchmark via Python
# ──────────────────────────────────────────────────────────────────────

$ioBenchScript = @"
import json, time, os, tempfile, sys
result = {"status": "skipped", "notes": ""}
TEST_DIR   = r'$TEST_DIR'
FILE_SIZE  = $FILE_SIZE * 1024 * 1024   # bytes
DURATION   = $DURATION
BLOCK_SIZE = 1 * 1024 * 1024            # 1 MB blocks

try:
    test_file = os.path.join(TEST_DIR, 'bee_bench_storage_tmp.bin')

    # ── Sequential Write ──────────────────────────────────────────────
    data = os.urandom(BLOCK_SIZE)
    total_written = 0
    t0 = time.perf_counter()
    deadline = t0 + min(DURATION, 15)
    with open(test_file, 'wb', buffering=0) as f:
        while time.perf_counter() < deadline and total_written < FILE_SIZE * 4:
            f.write(data)
            total_written += BLOCK_SIZE
    elapsed_w = time.perf_counter() - t0
    write_mbps = round(total_written / elapsed_w / (1024*1024), 2)

    # ── Sequential Read ───────────────────────────────────────────────
    # Write a fixed file first so we have something to read
    with open(test_file, 'wb', buffering=0) as f:
        f.write(data * (FILE_SIZE // BLOCK_SIZE))

    total_read = 0
    t0 = time.perf_counter()
    deadline = t0 + min(DURATION, 15)
    with open(test_file, 'rb', buffering=0) as f:
        while time.perf_counter() < deadline:
            chunk = f.read(BLOCK_SIZE)
            if not chunk:
                f.seek(0)
                continue
            total_read += len(chunk)
    elapsed_r = time.perf_counter() - t0
    read_mbps = round(total_read / elapsed_r / (1024*1024), 2)

    # ── 4K Random IOPS ───────────────────────────────────────────────
    BLOCK_4K   = 4096
    IOPS_LIMIT = 5000
    t0 = time.perf_counter()
    with open(test_file, 'r+b', buffering=0) as f:
        file_size = os.path.getsize(test_file)
        import random
        ops = 0
        deadline4k = t0 + min(DURATION, 10)
        while time.perf_counter() < deadline4k and ops < IOPS_LIMIT:
            offset = random.randint(0, max(0, file_size - BLOCK_4K)) & ~(BLOCK_4K-1)
            f.seek(offset)
            f.read(BLOCK_4K)
            ops += 1
    elapsed_iops = time.perf_counter() - t0
    iops_4k = round(ops / elapsed_iops, 0)

    os.remove(test_file)

    result["status"]      = "ok"
    result["read_mbps"]   = read_mbps
    result["write_mbps"]  = write_mbps
    result["iops_4k"]     = iops_4k
    result["file_size_mb"] = $FILE_SIZE
except Exception as e:
    result["status"] = "failed"
    result["notes"]  = str(e)
    try:
        if os.path.exists(test_file): os.remove(test_file)
    except: pass
print(json.dumps(result))
"@

try {
    $ioOut = & $PYTHON_BIN -c $ioBenchScript 2>&1
    $ioResult = $ioOut | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($ioResult) {
        $subtests["sequential_io"] = $ioResult
        if ($ioResult.status -ne "ok") {
            $status = "degraded"
            $notes.Add("Storage IO benchmark: $($ioResult.notes)")
        }
    }
} catch {
    $subtests["sequential_io"] = [ordered]@{ status = "failed"; notes = "$_" }
    $status = "degraded"
}

# Score: read throughput in MB/s
$score = if ($subtests["sequential_io"] -and $subtests["sequential_io"].read_mbps) {
    $subtests["sequential_io"].read_mbps
} else { $null }

# ──────────────────────────────────────────────────────────────────────
# Write result
# ──────────────────────────────────────────────────────────────────────

$result = [ordered]@{
    bench          = "disk"
    status         = $status
    score          = $score
    test_dir       = $TEST_DIR
    subtests       = $subtests
    notes          = ($notes | Out-String).Trim()
    schema_version = "1.0"
    platform       = "windows"
    ts             = (Get-Date -Format "o")
}

$result | ConvertTo-Json -Depth 8 | Set-Content -Path $OutJson -Encoding UTF8
Write-Host "[Storage] Done. Status=$status Score=$score MB/s -> $OutJson"
exit 0
