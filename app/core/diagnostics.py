"""
System diagnostics: CPU, GPU, RAM, OS detection.

Works on Linux (via /proc, sysfs, nvidia-smi) and Windows (via PowerShell
WMI queries / Get-CimInstance).  All detection is best-effort; missing
information is returned as empty string/zero rather than raising exceptions.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"
_IS_LINUX = platform.system() == "Linux"


@dataclass
class CpuInfo:
    model: str = ""
    cores_physical: int = 0
    cores_logical: int = 0
    architecture: str = ""
    frequency_mhz: float = 0.0
    vendor: str = ""


@dataclass
class GpuInfo:
    vendor: str = ""
    model: str = ""
    vram_mb: int = 0
    driver_version: str = ""
    backend: str = ""  # nvidia/amd/intel/unknown


@dataclass
class MemoryInfo:
    total_mb: int = 0
    available_mb: int = 0
    swap_total_mb: int = 0


@dataclass
class StorageInfo:
    device: str = ""
    type: str = ""  # ssd/hdd/nvme/unknown
    total_gb: float = 0.0
    free_gb: float = 0.0


@dataclass
class SystemInfo:
    hostname: str = ""
    os_name: str = ""
    os_version: str = ""
    kernel: str = ""
    cpu: CpuInfo = field(default_factory=CpuInfo)
    gpus: List[GpuInfo] = field(default_factory=list)
    memory: MemoryInfo = field(default_factory=MemoryInfo)
    storage: StorageInfo = field(default_factory=StorageInfo)
    python_version: str = ""
    arch: str = ""


def detect_system_info() -> SystemInfo:
    """Gather as much system information as possible without root/admin access."""
    info = SystemInfo()
    info.hostname = platform.node()
    info.os_name = _detect_os_name()
    info.os_version = platform.version()
    info.kernel = platform.release()
    info.python_version = platform.python_version()
    info.arch = platform.machine()

    if _IS_WINDOWS:
        info.cpu = _detect_cpu_windows()
        info.gpus = _detect_gpus_windows()
        info.memory = _detect_memory_windows()
        info.storage = _detect_storage_windows()
    else:
        info.cpu = _detect_cpu_linux()
        info.gpus = _detect_gpus_linux()
        info.memory = _detect_memory_linux()
        info.storage = _detect_storage_linux()

    return info


# ══════════════════════════════════════════════════════════════════════
#  WINDOWS detection
# ══════════════════════════════════════════════════════════════════════

def _ps_query(script: str, timeout: int = 8) -> str:
    """Run a PowerShell one-liner and return its stdout."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except Exception as exc:
        log.debug("PowerShell query failed: %s", exc)
        return ""


def _detect_cpu_windows() -> CpuInfo:
    cpu = CpuInfo()
    cpu.architecture = platform.machine()
    cpu.cores_logical = os.cpu_count() or 0

    # Get-CimInstance Win32_Processor
    out = _ps_query(
        "Get-CimInstance Win32_Processor | "
        "Select-Object -First 1 Name,NumberOfCores,MaxClockSpeed,Manufacturer | "
        "ConvertTo-Json -Depth 1 -Compress"
    )
    if out:
        try:
            import json
            d = json.loads(out)
            cpu.model = str(d.get("Name", "")).strip()
            cpu.cores_physical = int(d.get("NumberOfCores") or 0)
            cpu.frequency_mhz = float(d.get("MaxClockSpeed") or 0)
            cpu.vendor = str(d.get("Manufacturer", "")).strip()
        except Exception as exc:
            log.debug("CPU JSON parse failed: %s", exc)

    if not cpu.cores_physical:
        cpu.cores_physical = cpu.cores_logical

    return cpu


def _detect_gpus_windows() -> List[GpuInfo]:
    gpus: List[GpuInfo] = []

    # Try nvidia-smi first (works on Windows too)
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            out = _run_cmd([
                nvidia_smi,
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ])
            for line in out.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    vram = _parse_mb(parts[1])
                    gpus.append(GpuInfo(
                        vendor="NVIDIA",
                        model=parts[0],
                        vram_mb=vram,
                        driver_version=parts[2],
                        backend="nvidia",
                    ))
        except Exception as exc:
            log.debug("nvidia-smi query failed: %s", exc)

    if not gpus:
        # Fallback: Win32_VideoController via PowerShell
        out = _ps_query(
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name,AdapterRAM,DriverVersion | "
            "ConvertTo-Json -Depth 1 -Compress"
        )
        if out:
            try:
                import json
                items = json.loads(out)
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    name = str(item.get("Name", "")).strip()
                    if not name:
                        continue
                    vram_bytes = int(item.get("AdapterRAM") or 0)
                    vram_mb = vram_bytes // (1024 * 1024)
                    driver = str(item.get("DriverVersion", "")).strip()
                    vendor = "unknown"
                    if "NVIDIA" in name.upper():
                        vendor = "NVIDIA"
                        backend = "nvidia"
                    elif "AMD" in name.upper() or "RADEON" in name.upper():
                        vendor = "AMD"
                        backend = "amd"
                    elif "INTEL" in name.upper():
                        vendor = "Intel"
                        backend = "intel"
                    else:
                        backend = "unknown"
                    gpus.append(GpuInfo(
                        vendor=vendor, model=name,
                        vram_mb=vram_mb, driver_version=driver,
                        backend=backend,
                    ))
            except Exception as exc:
                log.debug("Win32_VideoController parse failed: %s", exc)

    return gpus


def _detect_memory_windows() -> MemoryInfo:
    mem = MemoryInfo()
    out = _ps_query(
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object TotalVisibleMemorySize,FreePhysicalMemory,TotalVirtualMemorySize | "
        "ConvertTo-Json -Depth 1 -Compress"
    )
    if out:
        try:
            import json
            d = json.loads(out)
            total_kb = int(d.get("TotalVisibleMemorySize") or 0)
            free_kb  = int(d.get("FreePhysicalMemory") or 0)
            virt_kb  = int(d.get("TotalVirtualMemorySize") or 0)
            mem.total_mb     = total_kb // 1024
            mem.available_mb = free_kb  // 1024
            mem.swap_total_mb = max(0, (virt_kb - total_kb) // 1024)
        except Exception as exc:
            log.debug("Memory parse failed: %s", exc)
    return mem


def _detect_storage_windows() -> StorageInfo:
    storage = StorageInfo()
    try:
        import shutil as _shutil
        total, used, free = _shutil.disk_usage("C:\\")
        storage.device = "C:\\"
        storage.total_gb = total / (1024 ** 3)
        storage.free_gb  = free  / (1024 ** 3)
        storage.type = _detect_disk_type_windows("C:")
    except Exception as exc:
        log.debug("Storage detection failed: %s", exc)
    return storage


def _detect_disk_type_windows(drive: str = "C:") -> str:
    out = _ps_query(
        f"$disk = Get-Partition -DriveLetter '{drive.rstrip(':')}' -ErrorAction SilentlyContinue | "
        f"Get-Disk -ErrorAction SilentlyContinue; "
        f"if ($disk) {{ $disk.MediaType }} else {{ 'Unknown' }}"
    )
    val = (out or "").strip().lower()
    if "ssd" in val:
        return "ssd"
    if "hdd" in val or "hard" in val:
        return "hdd"
    if "nvme" in val:
        return "nvme"
    return "unknown"


# ══════════════════════════════════════════════════════════════════════
#  LINUX detection
# ══════════════════════════════════════════════════════════════════════

def _detect_cpu_linux() -> CpuInfo:
    cpu = CpuInfo()
    cpu.architecture = platform.machine()

    try:
        cpu.cores_logical = os.cpu_count() or 0
    except Exception:
        pass

    try:
        with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        models = re.findall(r"model name\s*:\s*(.+)", text)
        if models:
            cpu.model = models[0].strip()
        vendors = re.findall(r"vendor_id\s*:\s*(.+)", text)
        if vendors:
            cpu.vendor = vendors[0].strip()
        phys = re.findall(r"cpu cores\s*:\s*(\d+)", text)
        if phys:
            cpu.cores_physical = int(phys[0])
        speeds = re.findall(r"cpu MHz\s*:\s*([\d.]+)", text)
        if speeds:
            vals = [float(s) for s in speeds]
            cpu.frequency_mhz = sum(vals) / len(vals)
    except Exception as exc:
        log.debug("CPU /proc/cpuinfo read failed: %s", exc)

    if not cpu.cores_physical:
        cpu.cores_physical = cpu.cores_logical

    return cpu


def _detect_gpus_linux() -> List[GpuInfo]:
    gpus: List[GpuInfo] = []

    # NVIDIA
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            out = _run_cmd([
                nvidia_smi,
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ])
            for line in out.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    vram = _parse_mb(parts[1])
                    gpus.append(GpuInfo(
                        vendor="NVIDIA",
                        model=parts[0],
                        vram_mb=vram,
                        driver_version=parts[2],
                        backend="nvidia",
                    ))
        except Exception as exc:
            log.debug("nvidia-smi query failed: %s", exc)

    # AMD via rocm-smi
    if not gpus:
        rocm_smi = shutil.which("rocm-smi")
        if rocm_smi:
            try:
                out = _run_cmd([rocm_smi, "--showname", "--showmeminfo", "vram"])
                if "AMD" in out or "Radeon" in out:
                    gpus.append(GpuInfo(vendor="AMD", model="AMD GPU (rocm-smi)", backend="amd"))
            except Exception as exc:
                log.debug("rocm-smi query failed: %s", exc)

    # Intel via sysfs
    if not gpus:
        try:
            sysfs = "/sys/class/drm"
            if os.path.isdir(sysfs):
                for card in sorted(os.listdir(sysfs)):
                    vendor_file = f"{sysfs}/{card}/device/vendor"
                    if os.path.exists(vendor_file):
                        with open(vendor_file) as fh:
                            vendor_id = fh.read().strip()
                        if vendor_id == "0x8086":
                            gpus.append(GpuInfo(vendor="Intel", model="Intel GPU", backend="intel"))
                            break
        except Exception as exc:
            log.debug("Intel GPU sysfs detection failed: %s", exc)

    if not gpus:
        glxinfo = shutil.which("glxinfo")
        if glxinfo:
            try:
                out = _run_cmd([glxinfo, "-B"])
                renderer = re.search(r"OpenGL renderer string:\s*(.+)", out)
                if renderer:
                    gpus.append(GpuInfo(model=renderer.group(1).strip(), backend="unknown"))
            except Exception as exc:
                log.debug("glxinfo failed: %s", exc)

    return gpus


def _detect_memory_linux() -> MemoryInfo:
    mem = MemoryInfo()
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            text = fh.read()
        total = re.search(r"MemTotal:\s+(\d+) kB", text)
        avail = re.search(r"MemAvailable:\s+(\d+) kB", text)
        swap  = re.search(r"SwapTotal:\s+(\d+) kB", text)
        if total:
            mem.total_mb     = int(total.group(1)) // 1024
        if avail:
            mem.available_mb = int(avail.group(1)) // 1024
        if swap:
            mem.swap_total_mb = int(swap.group(1)) // 1024
    except Exception as exc:
        log.debug("Memory detection from /proc/meminfo failed: %s", exc)
    return mem


def _detect_storage_linux() -> StorageInfo:
    storage = StorageInfo()
    try:
        stat = os.statvfs("/")
        total_bytes = stat.f_frsize * stat.f_blocks
        free_bytes  = stat.f_frsize * stat.f_bavail
        storage.total_gb = total_bytes / (1024 ** 3)
        storage.free_gb  = free_bytes  / (1024 ** 3)
        storage.device   = "/"
        storage.type     = _detect_disk_type_linux("/")
    except Exception as exc:
        log.debug("Storage detection failed: %s", exc)
    return storage


def _detect_disk_type_linux(mount_point: str) -> str:
    try:
        out = _run_cmd(["findmnt", "-n", "-o", "SOURCE", mount_point])
        device = out.strip().lstrip("/dev/")
        rot_path = f"/sys/block/{device.split('/')[0]}/queue/rotational"
        if os.path.exists(rot_path):
            with open(rot_path) as fh:
                rotational = fh.read().strip()
            return "ssd" if rotational == "0" else "hdd"
    except Exception:
        pass
    return "unknown"


# ══════════════════════════════════════════════════════════════════════
#  Cross-platform helpers
# ══════════════════════════════════════════════════════════════════════

def _detect_os_name() -> str:
    if _IS_WINDOWS:
        out = _ps_query(
            "(Get-CimInstance Win32_OperatingSystem).Caption"
        )
        if out:
            return out.strip()
    else:
        try:
            with open("/etc/os-release", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
    return platform.system()


def _run_cmd(cmd: List[str], timeout: int = 5) -> str:
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    return result.stdout


def _parse_mb(text: str) -> int:
    m = re.search(r"([\d.]+)\s*(MiB|MB|GiB|GB)?", text, re.IGNORECASE)
    if not m:
        return 0
    val = float(m.group(1))
    unit = (m.group(2) or "MB").upper()
    if "GI" in unit or "GB" in unit:
        return int(val * 1024)
    return int(val)


# Back-compat aliases so existing code doesn't break
_detect_cpu = _detect_cpu_windows if _IS_WINDOWS else _detect_cpu_linux
_detect_gpus = _detect_gpus_windows if _IS_WINDOWS else _detect_gpus_linux
_detect_memory = _detect_memory_windows if _IS_WINDOWS else _detect_memory_linux
_detect_storage = _detect_storage_windows if _IS_WINDOWS else _detect_storage_linux
