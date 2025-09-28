"""Utility for collecting a simple CI run report.

CIReport.update_report(app_path: str, return_code: int) -> None
    Record result for an application test invocation.

CIReport.generate_report() -> str
    Persist the collected report to a file and return its path.

The sessions_path points at a `.sessions/` directory under the current
working directory (created if missing) which can host per-run artifacts.
The final report is written under that directory as `ci_report.json` for
now (could become timestamped or more elaborate later).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
import json
import os
import csv
from datetime import datetime
from typing import Dict, List


@dataclass
class AppResult:
    app_path: str
    return_code: int
    status: str  # "ok" or "fail"
    timestamp: str
    detail_report: dict = field(default_factory=dict)


class CIReport:
    def __init__(self) -> None:
        # sessions directory under CWD
        self.sessions_path = os.path.join(os.getcwd(), ".sessions")
        os.makedirs(self.sessions_path, exist_ok=True)
        self._results: List[AppResult] = []
        # Could support incremental flush later

    def update_report(self, app_path: str, return_code: int) -> None:
        """Add result for an application. Automatically attempts to attach detail_report
        when the return_code indicates success (0)."""
        status = "ok" if return_code == 0 else "fail"
        result = AppResult(
            app_path=app_path,
            return_code=return_code,
            status=status,
            timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )
        self._results.append(result)
        if status == "ok":
            self._try_add_detail(result)

    # Backwards compatibility shim (if previously called externally). Now internal.
    def derail_report(self, app_path: str) -> None:  # pragma: no cover - transitional
        for r in reversed(self._results):
            if r.app_path == app_path and r.status == "ok":
                if not r.detail_report:
                    self._try_add_detail(r)
                return

    def _try_add_detail(self, result: AppResult) -> None:
        """Internal: attempt to enrich a successful result with detail csv data."""
        app_path = result.app_path
        cwd = os.getcwd()
        try:
            relative_app_path = os.path.relpath(app_path, cwd)
            if relative_app_path.startswith("../"):
                relative_app_path = relative_app_path[3:]
        except Exception:
            relative_app_path = app_path
        app_sessions_root = os.path.join(self.sessions_path, relative_app_path)

        if not os.path.isdir(app_sessions_root):
            return

        candidates = []
        try:
            for entry in os.listdir(app_sessions_root):
                full = os.path.join(app_sessions_root, entry)
                if os.path.isdir(full) and 'session' in entry.lower():
                    candidates.append(full)
        except FileNotFoundError:
            return
        if not candidates:
            return
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        session_subdir = candidates[0]

        run_csv = os.path.join(session_subdir, "reports", 'run_report.csv')
        build_csv = os.path.join(session_subdir, "reports", 'build_report.csv')

        def read_csv(path: str):
            if not os.path.isfile(path):
                return []
            rows = []
            try:
                with open(path, newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        rows.append(row)
            except Exception:
                return []
            return rows

        data = {
            'relative_app_path': relative_app_path,
            'session_folder': os.path.basename(session_subdir),
            'run_report': read_csv(run_csv),
            'build_report': read_csv(build_csv),
        }
        try:
            result.detail_report = data
        except Exception:
            result.detail_report = {}

    def generate_report(self) -> str:
        """Write a JSON report file and return its path.
        For now we overwrite a deterministic filename so external
        tooling can pick it up easily; could switch to timestamped.
        """
        data: Dict[str, object] = {
            "summary": {
                "total": len(self._results),
                "passed": sum(1 for r in self._results if r.status == "ok"),
                "failed": sum(1 for r in self._results if r.status == "fail"),
            },
            "results": [asdict(r) for r in self._results],
        }
        out_path = os.path.join(self.sessions_path, "ci_report.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return out_path


__all__ = ["CIReport"]
