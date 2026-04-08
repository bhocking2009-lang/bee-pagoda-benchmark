"""
New Benchmark Run form view.

Lets the user choose profile, categories, and advanced options,
then emits run_requested(RunRequest).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.profiles import list_profiles
from app.core.runner import RunRequest

_ROOT = Path(__file__).parent.parent.parent.parent

_CATEGORY_LABELS = {
    "cpu":         "CPU  (sysbench / openssl / ffmpeg)",
    "gpu_compute": "GPU Compute  (clpeak / hashcat)",
    "gpu_game":    "GPU Graphics  (game-style workload)",
    "ai":          "AI  (llama.cpp / ONNX / PyTorch)",
    "memory":      "Memory  (mbw / stream)",
    "disk":        "Storage  (fio / dd)",
}


class RunView(QWidget):
    """Benchmark configuration form."""

    run_requested = Signal(object)   # RunRequest

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # Header
        title = QLabel("New Benchmark Run")
        title.setObjectName("SectionHeader")
        root.addWidget(title)
        sub = QLabel("Configure the benchmark suite and launch a run.")
        sub.setObjectName("SubHeader")
        root.addWidget(sub)

        # Scroll area for the form body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setSpacing(20)
        body_layout.setContentsMargins(0, 0, 16, 0)
        scroll.setWidget(body)
        root.addWidget(scroll)

        # ── Profile ─────────────────────────────────────────────────────
        profile_group = QGroupBox("Benchmark Profile")
        pg_layout = QHBoxLayout(profile_group)
        pg_layout.setSpacing(16)

        self._profile_combo = QComboBox()
        profiles = list_profiles()
        if not profiles:
            profiles = ["quick", "balanced", "deep"]
        for p in profiles:
            self._profile_combo.addItem(p.capitalize(), p)
        # Default to balanced
        for i in range(self._profile_combo.count()):
            if self._profile_combo.itemData(i) == "balanced":
                self._profile_combo.setCurrentIndex(i)
                break

        pg_layout.addWidget(QLabel("Profile:"))
        pg_layout.addWidget(self._profile_combo)
        pg_layout.addStretch()
        body_layout.addWidget(profile_group)

        # ── Categories ──────────────────────────────────────────────────
        cat_group = QGroupBox("Benchmark Categories")
        cat_layout = QGridLayout(cat_group)
        cat_layout.setSpacing(10)

        self._cat_checks: dict[str, QCheckBox] = {}
        for i, (cat_id, cat_label) in enumerate(_CATEGORY_LABELS.items()):
            cb = QCheckBox(cat_label)
            cb.setChecked(True)
            self._cat_checks[cat_id] = cb
            cat_layout.addWidget(cb, i // 2, i % 2)

        all_row = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_none = QPushButton("Deselect All")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none.clicked.connect(lambda: self._set_all(False))
        all_row.addWidget(btn_all)
        all_row.addWidget(btn_none)
        all_row.addStretch()
        cat_layout.addLayout(all_row, (len(_CATEGORY_LABELS) // 2) + 1, 0, 1, 2)
        body_layout.addWidget(cat_group)

        # ── Advanced options ─────────────────────────────────────────────
        adv_group = QGroupBox("Advanced Options")
        adv_layout = QGridLayout(adv_group)
        adv_layout.setSpacing(10)

        adv_layout.addWidget(QLabel("Python interpreter:"), 0, 0)
        self._python_edit = QLineEdit()
        self._python_edit.setPlaceholderText("(auto-detect)")
        adv_layout.addWidget(self._python_edit, 0, 1)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse_python)
        adv_layout.addWidget(btn_browse, 0, 2)

        self._skip_preflight_cb = QCheckBox("Skip preflight dependency checks")
        adv_layout.addWidget(self._skip_preflight_cb, 1, 0, 1, 3)

        adv_layout.addWidget(QLabel("GPU game mode:"), 2, 0)
        self._gpu_mode_combo = QComboBox()
        for mode in ("offscreen", "auto", "interactive"):
            self._gpu_mode_combo.addItem(mode, mode)
        adv_layout.addWidget(self._gpu_mode_combo, 2, 1)

        adv_layout.addWidget(QLabel("AI backends:"), 3, 0)
        ai_backend_row = QHBoxLayout()
        self._ai_llama_cb = QCheckBox("llama.cpp")
        self._ai_torch_cb = QCheckBox("PyTorch")
        self._ai_onnx_cb  = QCheckBox("ONNX Runtime")
        for cb in (self._ai_llama_cb, self._ai_torch_cb, self._ai_onnx_cb):
            cb.setChecked(True)
            ai_backend_row.addWidget(cb)
        ai_backend_row.addStretch()
        ai_container = QWidget()
        ai_container.setLayout(ai_backend_row)
        adv_layout.addWidget(ai_container, 3, 1, 1, 2)

        body_layout.addWidget(adv_group)

        # ── Output directory preview ─────────────────────────────────────
        out_frame = QFrame()
        out_frame.setObjectName("Card")
        out_layout = QVBoxLayout(out_frame)
        out_layout.setContentsMargins(16, 12, 16, 12)
        out_layout.addWidget(QLabel("Output directory"))
        reports_path = _ROOT / "reports"
        self._output_label = QLabel(f"<code>{reports_path}/run-&lt;timestamp&gt;-&lt;profile&gt;/</code>")
        self._output_label.setObjectName("MutedLabel")
        out_layout.addWidget(self._output_label)
        body_layout.addWidget(out_frame)

        body_layout.addStretch()

        # ── Launch button ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._launch_btn = QPushButton("▶  Start Benchmark")
        self._launch_btn.setObjectName("PrimaryButton")
        self._launch_btn.setMinimumWidth(200)
        self._launch_btn.clicked.connect(self._on_launch)
        btn_row.addWidget(self._launch_btn)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _set_all(self, checked: bool) -> None:
        for cb in self._cat_checks.values():
            cb.setChecked(checked)

    def _browse_python(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Python Interpreter")
        if path:
            self._python_edit.setText(path)

    def _on_launch(self) -> None:
        profile = self._profile_combo.currentData() or "balanced"
        categories = [cat for cat, cb in self._cat_checks.items() if cb.isChecked()]
        python_bin = self._python_edit.text().strip() or None
        skip_preflight = self._skip_preflight_cb.isChecked()
        gpu_mode = self._gpu_mode_combo.currentData() or "offscreen"

        env: dict[str, str] = {}
        if not self._ai_llama_cb.isChecked():
            env["AI_ENABLE_LLAMA"] = "0"
        if not self._ai_torch_cb.isChecked():
            env["AI_ENABLE_TORCH"] = "0"
        if not self._ai_onnx_cb.isChecked():
            env["AI_ENABLE_ONNXRUNTIME"] = "0"
        env["GPU_GAME_MODE"] = gpu_mode

        req = RunRequest(
            profile=profile,
            categories=categories,
            python_bin=python_bin,
            skip_preflight=skip_preflight,
            extra_env=env,
        )
        self.run_requested.emit(req)

    def set_enabled(self, enabled: bool) -> None:
        """Disable form while a run is in progress."""
        self._launch_btn.setEnabled(enabled)
        self._profile_combo.setEnabled(enabled)
        for cb in self._cat_checks.values():
            cb.setEnabled(enabled)

    def preset_profile(self, profile: str) -> None:
        """Pre-select a profile (called from dashboard quick launch)."""
        for i in range(self._profile_combo.count()):
            if self._profile_combo.itemData(i) == profile:
                self._profile_combo.setCurrentIndex(i)
                break
