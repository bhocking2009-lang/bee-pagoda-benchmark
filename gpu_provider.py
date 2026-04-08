"""GPU provider abstraction layer.

Defines the GpuProvider interface and factory function used by benchmark
scripts.  Each provider wraps vendor-specific detection and enrichment,
returning a normalized dict of GPU metadata.

Providers available:
- NvidiaProvider  (nvidia-smi)
- AmdProvider     (rocm-smi / radeontop)
- IntelProvider   (intel_gpu_top / xpu-smi)
- GenericProvider (fallback via Vulkan / lspci)
"""
from __future__ import annotations

import subprocess
import os
from abc import ABC, abstractmethod
from typing import Optional


class GpuProvider(ABC):
    """Abstract GPU provider contract."""

    @classmethod
    @abstractmethod
    def detect(cls) -> bool:
        """Return True when this vendor's GPU is present and tools are available."""

    @abstractmethod
    def preflight(self) -> dict:
        """Return a preflight dict: {name, status, version, path, notes}."""

    @abstractmethod
    def normalize_metrics(self, raw: dict) -> dict:
        """Normalize vendor-specific raw metrics to common fields."""

    # Optional enrichment: best-effort, must never raise
    def enrich(self) -> dict:
        """Return vendor-specific supplementary metadata (best-effort)."""
        return {}


# ---- helpers ----

def _run(*cmd, default="") -> str:
    try:
        return subprocess.check_output(list(cmd), stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return default


def _has_cmd(cmd: str) -> bool:
    try:
        subprocess.run(["which", cmd], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# ---- Providers ----

class NvidiaProvider(GpuProvider):
    """NVIDIA GPU provider (nvidia-smi)."""

    @classmethod
    def detect(cls) -> bool:
        return _has_cmd("nvidia-smi")

    def preflight(self) -> dict:
        version = _run("nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader")
        cuda = _run("nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader")
        model = _run("nvidia-smi", "--query-gpu=name", "--format=csv,noheader")
        status = "present" if version else "missing"
        return {
            "name": "nvidia-smi",
            "vendor": "nvidia",
            "status": status,
            "version": version,
            "path": _run("which", "nvidia-smi"),
            "notes": f"model={model} cuda_cap={cuda}",
        }

    def enrich(self) -> dict:
        model = _run("nvidia-smi", "--query-gpu=name", "--format=csv,noheader")
        driver = _run("nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader")
        vram_mib = _run("nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits")
        temp = _run("nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader")
        power_w = _run("nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits")
        return {
            "vendor": "nvidia",
            "model": model,
            "driver": driver,
            "vram_mib": vram_mib,
            "temperature_c": temp,
            "power_w": power_w,
        }

    def normalize_metrics(self, raw: dict) -> dict:
        return {
            "vendor": "nvidia",
            "score": raw.get("score"),
            "fps": raw.get("fps"),
            "frametime_ms": raw.get("frametime_ms"),
            "gflops": raw.get("gflops"),
        }


class AmdProvider(GpuProvider):
    """AMD GPU provider (rocm-smi / radeontop)."""

    @classmethod
    def detect(cls) -> bool:
        return _has_cmd("rocm-smi") or _has_cmd("radeontop")

    def preflight(self) -> dict:
        if _has_cmd("rocm-smi"):
            tool = "rocm-smi"
            version = _run("rocm-smi", "--version")
            path = _run("which", "rocm-smi")
        else:
            tool = "radeontop"
            version = _run("radeontop", "--version")
            path = _run("which", "radeontop")
        status = "present" if version else "degraded"
        model = _run("bash", "-c", "lspci | grep -i 'amd\\|radeon' | head -n1")
        return {
            "name": tool,
            "vendor": "amd",
            "status": status,
            "version": version,
            "path": path,
            "notes": f"model={model}",
        }

    def enrich(self) -> dict:
        model = _run("bash", "-c", "lspci | grep -i 'amd\\|radeon' | head -n1")
        driver = _run("bash", "-c", "modinfo amdgpu 2>/dev/null | grep '^version:' | awk '{print $2}' | head -n1")
        return {
            "vendor": "amd",
            "model": model,
            "driver": driver,
        }

    def normalize_metrics(self, raw: dict) -> dict:
        return {
            "vendor": "amd",
            "score": raw.get("score"),
            "fps": raw.get("fps"),
            "frametime_ms": raw.get("frametime_ms"),
            "gflops": raw.get("gflops"),
        }


class IntelProvider(GpuProvider):
    """Intel GPU provider (intel_gpu_top / xpu-smi)."""

    @classmethod
    def detect(cls) -> bool:
        return _has_cmd("intel_gpu_top") or _has_cmd("xpu-smi")

    def preflight(self) -> dict:
        if _has_cmd("xpu-smi"):
            tool = "xpu-smi"
            version = _run("xpu-smi", "version")
            path = _run("which", "xpu-smi")
        else:
            tool = "intel_gpu_top"
            version = _run("intel_gpu_top", "--version")
            path = _run("which", "intel_gpu_top")
        status = "present" if path else "degraded"
        model = _run("bash", "-c", r"lspci | grep -i 'intel.*\(vga\|3d\|display\)' | head -n1")
        return {
            "name": tool,
            "vendor": "intel",
            "status": status,
            "version": version,
            "path": path,
            "notes": f"model={model}",
        }

    def enrich(self) -> dict:
        model = _run("bash", "-c", "lspci | grep -i intel | grep -iE 'vga|3d|display' | head -n1")
        return {
            "vendor": "intel",
            "model": model,
        }

    def normalize_metrics(self, raw: dict) -> dict:
        return {
            "vendor": "intel",
            "score": raw.get("score"),
            "fps": raw.get("fps"),
            "frametime_ms": raw.get("frametime_ms"),
        }


class GenericProvider(GpuProvider):
    """Generic fallback provider (lspci / Vulkan hints)."""

    @classmethod
    def detect(cls) -> bool:
        return True  # always available as last resort

    def preflight(self) -> dict:
        model = _run("bash", "-c", "lspci | grep -iE '(vga|3d|display)' | head -n1")
        return {
            "name": "generic",
            "vendor": "generic",
            "status": "degraded",
            "version": "",
            "path": "",
            "notes": f"model={model or 'unknown'}",
        }

    def enrich(self) -> dict:
        model = _run("bash", "-c", "lspci | grep -iE '(vga|3d|display)' | head -n1")
        vulkan_info = _run("bash", "-c", "vulkaninfo --summary 2>/dev/null | grep 'GPU id' | head -n1")
        return {
            "vendor": "generic",
            "model": model,
            "vulkan_hint": vulkan_info,
        }

    def normalize_metrics(self, raw: dict) -> dict:
        return {
            "vendor": "generic",
            "score": raw.get("score"),
            "fps": raw.get("fps"),
            "frametime_ms": raw.get("frametime_ms"),
        }


# ---- Factory ----

_PROVIDERS: list[type[GpuProvider]] = [
    NvidiaProvider,
    AmdProvider,
    IntelProvider,
    GenericProvider,
]


def get_provider() -> GpuProvider:
    """Detect GPU vendor and return the appropriate provider instance.

    Detection order: NVIDIA → AMD → Intel → Generic (fallback).
    """
    for cls in _PROVIDERS:
        try:
            if cls.detect():
                return cls()
        except Exception:
            continue
    return GenericProvider()


def detect_metadata() -> dict:
    """Return a dict with vendor_detected, provider_selected, provider_mode, and enrichment."""
    provider = get_provider()
    vendor = provider.__class__.__name__.replace("Provider", "").lower()
    enrichment = {}
    try:
        enrichment = provider.enrich()
    except Exception:
        pass
    return {
        "vendor_detected": enrichment.get("vendor", vendor),
        "provider_selected": provider.__class__.__name__,
        "provider_mode": "vendor_specific" if not isinstance(provider, GenericProvider) else "generic_fallback",
        **enrichment,
    }
