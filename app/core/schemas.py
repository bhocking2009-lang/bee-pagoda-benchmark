"""
Typed data models for benchmark results.

These dataclasses represent the canonical data contract between the shell
benchmark scripts, the Python engine, and the GUI.  All JSON result files
are loaded into these models via result_loader.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"


class BenchmarkStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    SKIPPED = "skipped"
    FAILED = "failed"
    MISSING = "missing"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str) -> "BenchmarkStatus":
        try:
            return cls(value.lower())
        except (ValueError, AttributeError):
            return cls.UNKNOWN


@dataclass
class SubtestResult:
    status: str = BenchmarkStatus.UNKNOWN.value
    tool: str = ""
    score: Optional[float] = None
    elapsed_sec: Optional[float] = None
    notes: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SubtestResult":
        return cls(
            status=str(d.get("status", BenchmarkStatus.UNKNOWN.value)),
            tool=str(d.get("tool", "")),
            score=_to_float(d.get("score")),
            elapsed_sec=_to_float(d.get("elapsed_sec")),
            notes=str(d.get("notes", "")),
            raw=d,
        )


@dataclass
class BackendResult:
    backend: str = ""
    status: str = BenchmarkStatus.UNKNOWN.value
    benchmark: str = ""
    primary_metric: str = ""
    data_source: str = ""
    score: Optional[float] = None
    prompt_tps: Optional[float] = None
    eval_tps: Optional[float] = None
    model: Optional[str] = None
    context_size: Optional[int] = None
    batch_size: Optional[int] = None
    notes: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BackendResult":
        return cls(
            backend=str(d.get("backend", "")),
            status=str(d.get("status", BenchmarkStatus.UNKNOWN.value)),
            benchmark=str(d.get("benchmark", "")),
            primary_metric=str(d.get("primary_metric", "")),
            data_source=str(d.get("data_source", "")),
            score=_to_float(d.get("score")),
            prompt_tps=_to_float(d.get("prompt_tps")),
            eval_tps=_to_float(d.get("eval_tps")),
            model=d.get("model"),
            context_size=_to_int(d.get("context_size")),
            batch_size=_to_int(d.get("batch_size")),
            notes=str(d.get("notes", "")),
            raw=d,
        )


@dataclass
class CompositeScore:
    value: Optional[float] = None
    formula: str = ""
    weighted: bool = False
    notes: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CompositeScore":
        return cls(
            value=_to_float(d.get("value")),
            formula=str(d.get("formula", "")),
            weighted=bool(d.get("weighted", False)),
            notes=str(d.get("notes", "")),
        )


@dataclass
class CategoryResult:
    category: str = ""
    status: str = BenchmarkStatus.UNKNOWN.value
    benchmark: str = ""
    primary_metric: str = ""
    score: Optional[float] = None
    fps: Optional[float] = None
    frametime_ms: Optional[float] = None
    prompt_tps: Optional[float] = None
    eval_tps: Optional[float] = None
    backend: str = ""
    data_source: str = ""
    model: Optional[str] = None
    context_size: Optional[int] = None
    batch_size: Optional[int] = None
    credible_ai_mode: Optional[bool] = None
    subtests: Dict[str, SubtestResult] = field(default_factory=dict)
    backend_results: List[BackendResult] = field(default_factory=list)
    composite: Optional[CompositeScore] = None
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CategoryResult":
        subtests: Dict[str, SubtestResult] = {}
        for k, v in d.get("subtests", {}).items():
            if isinstance(v, dict):
                subtests[k] = SubtestResult.from_dict(v)

        backend_results: List[BackendResult] = [
            BackendResult.from_dict(b)
            for b in d.get("backend_results", [])
            if isinstance(b, dict)
        ]

        composite: Optional[CompositeScore] = None
        if isinstance(d.get("composite"), dict):
            composite = CompositeScore.from_dict(d["composite"])

        return cls(
            category=str(d.get("category", "")),
            status=str(d.get("status", BenchmarkStatus.UNKNOWN.value)),
            benchmark=str(d.get("benchmark", "")),
            primary_metric=str(d.get("primary_metric", "")),
            score=_to_float(d.get("score")),
            fps=_to_float(d.get("fps")),
            frametime_ms=_to_float(d.get("frametime_ms")),
            prompt_tps=_to_float(d.get("prompt_tps")),
            eval_tps=_to_float(d.get("eval_tps")),
            backend=str(d.get("backend", "")),
            data_source=str(d.get("data_source", "")),
            model=d.get("model"),
            context_size=_to_int(d.get("context_size")),
            batch_size=_to_int(d.get("batch_size")),
            credible_ai_mode=d.get("credible_ai_mode"),
            subtests=subtests,
            backend_results=backend_results,
            composite=composite,
            diagnostics=d.get("diagnostics", {}),
            notes=str(d.get("notes", "")),
            raw=d,
        )

    @property
    def status_enum(self) -> BenchmarkStatus:
        return BenchmarkStatus.from_str(self.status)


@dataclass
class PreflightCheck:
    name: str = ""
    type: str = ""
    required: bool = False
    status: str = ""
    version: str = ""
    min_version: str = ""
    path: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PreflightCheck":
        return cls(
            name=str(d.get("name", "")),
            type=str(d.get("type", "")),
            required=bool(d.get("required", False)),
            status=str(d.get("status", "")),
            version=str(d.get("version", "")),
            min_version=str(d.get("min_version", "")),
            path=str(d.get("path", "")),
            notes=str(d.get("notes", "")),
        )


@dataclass
class PreflightResult:
    status: str = ""
    generated_at: str = ""
    checks: List[PreflightCheck] = field(default_factory=list)
    status_counts: Dict[str, int] = field(default_factory=dict)
    interpreter: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PreflightResult":
        checks = [
            PreflightCheck.from_dict(c)
            for c in d.get("checks", [])
            if isinstance(c, dict)
        ]
        return cls(
            status=str(d.get("status", "")),
            generated_at=str(d.get("generated_at", "")),
            checks=checks,
            status_counts=d.get("status_counts", {}),
            interpreter=str(d.get("interpreter", "")),
            notes=str(d.get("notes", "")),
        )


@dataclass
class RunMetadata:
    """Full result of one benchmark run, loaded from a run directory."""

    run_id: str = ""
    run_dir: str = ""
    profile: str = ""
    selected_categories: List[str] = field(default_factory=list)
    generated_at: str = ""
    suite_interpreter: str = ""
    schema_version: str = SCHEMA_VERSION
    preflight: Optional[PreflightResult] = None
    results: Dict[str, CategoryResult] = field(default_factory=dict)
    overall_status: str = BenchmarkStatus.UNKNOWN.value

    @classmethod
    def from_dict(cls, d: Dict[str, Any], run_id: str = "", run_dir: str = "") -> "RunMetadata":
        preflight: Optional[PreflightResult] = None
        if isinstance(d.get("preflight"), dict):
            preflight = PreflightResult.from_dict(d["preflight"])

        results: Dict[str, CategoryResult] = {}
        for k, v in d.get("results", {}).items():
            if isinstance(v, dict):
                results[k] = CategoryResult.from_dict(v)

        overall = _compute_overall_status(results)

        return cls(
            run_id=run_id or d.get("run_id", ""),
            run_dir=run_dir or d.get("run_dir", ""),
            profile=str(d.get("profile", "")),
            selected_categories=d.get("selected_categories", []),
            generated_at=str(d.get("generated_at", "")),
            suite_interpreter=str(d.get("suite_interpreter", "")),
            schema_version=str(d.get("schema_version", SCHEMA_VERSION)),
            preflight=preflight,
            results=results,
            overall_status=overall,
        )

    @property
    def category_count(self) -> int:
        return len(self.results)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results.values() if r.status == BenchmarkStatus.FAILED.value)

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results.values() if r.status == BenchmarkStatus.OK.value)


def _compute_overall_status(results: Dict[str, CategoryResult]) -> str:
    if not results:
        return BenchmarkStatus.UNKNOWN.value
    statuses = [r.status for r in results.values()]
    if any(s == BenchmarkStatus.FAILED.value for s in statuses):
        return BenchmarkStatus.FAILED.value
    if any(s == BenchmarkStatus.DEGRADED.value for s in statuses):
        return BenchmarkStatus.DEGRADED.value
    if all(s == BenchmarkStatus.SKIPPED.value for s in statuses):
        return BenchmarkStatus.SKIPPED.value
    if all(s == BenchmarkStatus.OK.value for s in statuses):
        return BenchmarkStatus.OK.value
    return BenchmarkStatus.DEGRADED.value


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        f = float(value)
        return None if (f != f) else f  # NaN guard
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> Optional[int]:
    f = _to_float(value)
    return int(f) if f is not None else None
