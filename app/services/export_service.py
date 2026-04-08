"""
ExportService: export benchmark results to various formats.

Supported actions:
  - Copy Markdown summary to clipboard (via Qt or xclip fallback)
  - Export summary JSON to a user-chosen path
  - Export summary CSV to a user-chosen path
  - Open the run's report folder in the system file manager
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.core.schemas import RunMetadata

log = logging.getLogger(__name__)


class ExportService:
    def __init__(self, run: RunMetadata) -> None:
        self.run = run
        self._run_dir = Path(run.run_dir)

    # ------------------------------------------------------------------
    # File access
    # ------------------------------------------------------------------

    @property
    def report_dir(self) -> Path:
        return self._run_dir / "report"

    @property
    def summary_md_path(self) -> Optional[Path]:
        p = self.report_dir / "summary.md"
        return p if p.exists() else None

    @property
    def summary_json_path(self) -> Optional[Path]:
        p = self.report_dir / "summary.json"
        return p if p.exists() else None

    @property
    def summary_csv_path(self) -> Optional[Path]:
        p = self.report_dir / "summary.csv"
        return p if p.exists() else None

    def read_summary_markdown(self) -> str:
        if self.summary_md_path:
            return self.summary_md_path.read_text(encoding="utf-8")
        return self._generate_inline_markdown()

    def read_summary_json(self) -> str:
        if self.summary_json_path:
            return self.summary_json_path.read_text(encoding="utf-8")
        return json.dumps(
            {"run_id": self.run.run_id, "profile": self.run.profile,
             "generated_at": self.run.generated_at},
            indent=2,
        )

    # ------------------------------------------------------------------
    # Export actions
    # ------------------------------------------------------------------

    def copy_markdown_to_clipboard(self) -> bool:
        """Copy Markdown summary to system clipboard.  Returns True on success."""
        text = self.read_summary_markdown()
        # Try Qt clipboard first (caller should pass a QApplication instance)
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                clipboard = app.clipboard()
                clipboard.setText(text)
                return True
        except Exception:
            pass
        # Fallback: xclip / xsel
        for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
            if shutil.which(cmd[0]):
                try:
                    proc = subprocess.run(cmd, input=text, text=True, timeout=5)
                    return proc.returncode == 0
                except Exception:
                    pass
        log.warning("No clipboard mechanism available")
        return False

    def export_json(self, dest_path: str | Path) -> bool:
        """Copy or generate the summary JSON to *dest_path*."""
        try:
            content = self.read_summary_json()
            Path(dest_path).write_text(content, encoding="utf-8")
            return True
        except Exception as exc:
            log.error("JSON export failed: %s", exc)
            return False

    def export_csv(self, dest_path: str | Path) -> bool:
        """Copy the summary CSV to *dest_path*."""
        try:
            if self.summary_csv_path:
                shutil.copy2(self.summary_csv_path, dest_path)
            else:
                self._generate_csv(dest_path)
            return True
        except Exception as exc:
            log.error("CSV export failed: %s", exc)
            return False

    def open_report_folder(self) -> bool:
        """Open the report folder in the system file manager."""
        import platform
        folder = self.report_dir if self.report_dir.exists() else self._run_dir
        system = platform.system()
        if system == "Windows":
            try:
                subprocess.Popen(["explorer", str(folder)])
                return True
            except Exception as exc:
                log.warning("explorer failed: %s", exc)
            return False
        elif system == "Darwin":
            try:
                subprocess.Popen(["open", str(folder)])
                return True
            except Exception as exc:
                log.warning("open failed: %s", exc)
            return False
        else:
            for cmd in (["xdg-open"], ["nautilus"], ["dolphin"], ["thunar"]):
                if shutil.which(cmd[0]):
                    try:
                        subprocess.Popen([cmd[0], str(folder)])
                        return True
                    except Exception:
                        pass
        log.warning("No file manager found to open folder: %s", folder)
        return False

    # ------------------------------------------------------------------
    # Inline generation fallbacks
    # ------------------------------------------------------------------

    def _generate_inline_markdown(self) -> str:
        lines = [
            f"# Benchmark Report — {self.run.run_id}",
            "",
            f"- **Profile:** {self.run.profile}",
            f"- **Generated:** {self.run.generated_at}",
            f"- **Status:** {self.run.overall_status}",
            "",
            "## Results",
            "",
            "| Category | Status | Score |",
            "|---|---|---|",
        ]
        for cat, result in self.run.results.items():
            score = result.score or result.fps or result.prompt_tps or ""
            lines.append(f"| {cat} | {result.status} | {score} |")
        return "\n".join(lines) + "\n"

    def _generate_csv(self, dest_path: str | Path) -> None:
        import csv
        with open(dest_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["category", "status", "score", "fps", "prompt_tps", "notes"])
            for cat, r in self.run.results.items():
                w.writerow([cat, r.status, r.score or "", r.fps or "",
                             r.prompt_tps or "", r.notes])
