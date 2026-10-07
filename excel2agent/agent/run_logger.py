"""Persists every agent run.

* ``logs/agent_runs.jsonl``  - full run records (request, routing, steps, status)
* ``logs/execution_log.csv`` - one row per executed step, in the SAME schema as
  ``data/workflow_execution_logs.csv``. This means WF010 (Workflow Performance
  Report) can analyse the agent's own live history with ``source=live``.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import RunResult

LOG_COLUMNS = ["timestamp", "run_id", "workflow_id", "workflow_name", "step_name",
               "status", "duration_ms", "error_message"]


class RunLogger:
    def __init__(self, base_dir: Path):
        self.dir = Path(base_dir) / "logs"

    def log(self, result: RunResult) -> None:
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with open(self.dir / "agent_runs.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"timestamp": now, **result.to_dict()}, default=str) + "\n")
            if not result.workflow_id:
                return
            path = self.dir / "execution_log.csv"
            new = not path.exists()
            with open(path, "a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=LOG_COLUMNS)
                if new:
                    w.writeheader()
                for st in result.steps:
                    w.writerow({"timestamp": now, "run_id": result.run_id, "workflow_id": result.workflow_id,
                                "workflow_name": result.workflow_name, "step_name": st.label,
                                "status": "success" if st.status in ("ok", "skipped", "halted") else "failed",
                                "duration_ms": st.duration_ms, "error_message": st.error or ""})
        except OSError:
            pass  # logging must never break a run
