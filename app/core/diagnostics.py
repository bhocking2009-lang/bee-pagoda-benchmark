"""
System diagnostics: CPU, GPU, RAM, OS detection.

All detection is best-effort; missing information is returned as empty
string rather than raising exceptions so the GUI always has something to
show even on unusual hardware configurations.
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
    """Gather as much system information as possible without root access."""
    info = SystemInfo()
    info.hostname = platform.node()
    info.os_name = _detect_os_name()
    info.os_version = platform.version()
    info.kernel = platform.release()
    info.python_version = platform.python_version()
    info.arch = platform.machine()
    info.cpu = _detect_cpu()
    info.gpus = _detect_gpus()
    info.memory = _detect_memory()
    info.storage = _detect_storage()
    return info


# ------------------------------------------------------------------
# CPU detection
# ------------------------------------------------------------------

def _detect_cpu() -> CpuInfo:
    cpu = CpuInfo()
    cpu.architecture = platform.machine()

    try:
        import os as _os
        cpu.cores_logical = _os.cpu_count() or 0
    except Exception:
        pass

    # Try /proc/cpuinfo
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


# ------------------------------------------------------------------
# GPU detection
# ------------------------------------------------------------------

def _detect_gpus() -> List[GpuInfo]:
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

    # Intel via sysfs / glxinfo fallback
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
        # Last resort: glxinfo
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


# ------------------------------------------------------------------
# Memory detection
# ------------------------------------------------------------------

def _detect_memory() -> MemoryInfo:
    mem = MemoryInfo()
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            text = fh.read()
        total = re.search(r"MemTotal:\s+(\d+) kB", text)
        avail = re.search(r"MemAvailable:\s+(\d+) kB", text)
        swap = re.search(r"SwapTotal:\s+(\d+) kB", text)
        if total:
            mem.total_mb = int(total.group(1)) // 1024
        if avail:
            mem.available_mb = int(avail.group(1)) // 1024
        if swap:
            mem.swap_total_mb = int(swap.group(1)) // 1024
    except Exception as exc:
        log.debug("Memory detection from /proc/meminfo failed: %s", exc)
    return mem


# ------------------------------------------------------------------
# Storage detection
# ------------------------------------------------------------------

def _detect_storage() -> StorageInfo:
    storage = StorageInfo()
    try:
        stat = os.statvfs("/")
        total_bytes = stat.f_frsize * stat.f_blocks
        free_bytes = stat.f_frsize * stat.f_bavail
        storage.total_gb = total_bytes / (1024 ** 3)
        storage.free_gb = free_bytes / (1024 ** 3)
        storage.device = "/"
        storage.type = _detect_disk_type("/")
    except Exception as exc:
        log.debug("Storage detection failed: %s", exc)
    return storage


def _detect_disk_type(mount_point: str) -> str:
    try:
        # Find the underlying device for the mount point
        out = _run_cmd(["findmnt", "-n", "-o", "SOURCE", mount_point])
        device = out.strip().lstrip("/dev/")
        # Check rotational flag
        rot_path = f"/sys/block/{device.split('/')[0]}/queue/rotational"
        if os.path.exists(rot_path):
            with open(rot_path) as fh:
                rotational = fh.read().strip()
            if rotational == "0":
                return "ssd"
            return "hdd"
    except Exception:
        pass
    return "unknown"


# ------------------------------------------------------------------
# OS detection
# ------------------------------------------------------------------

def _detect_os_name() -> str:
    try:
        with open("/etc/os-release", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return platform.system()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

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
