"""Workflow registry: Excel (business definition) + YAML (execution binding).

The Excel file is the single source of truth for *what* each workflow is: name,
trigger, inputs, ordered steps, decision logic, tools and expected output.
``config/workflow_bindings.yaml`` only says *how* each Excel step is executed
(which registered tool, with which arguments). The registry merges both and
cross-validates them so the two can never silently drift apart.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import openpyxl
import yaml

from .models import ParamSpec, StepBinding, WorkflowSpec
from .tools import all_tools

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXCEL = PROJECT_ROOT / "workflows" / "AI_Agent_Workflow_Assessment.xlsx"
DEFAULT_BINDINGS = PROJECT_ROOT / "config" / "workflow_bindings.yaml"

EXCEL_COLUMNS = ["Workflow_ID", "Workflow_Name", "Trigger", "Inputs", "Steps",
                 "Decision_Logic", "Tools_Required", "Expected_Output"]
STEP_SPLIT = re.compile(r"\s*(?:→|->|=>)\s*")


@dataclass
class ValidationIssue:
    level: str          # error | warning
    workflow_id: str
    message: str


@dataclass
class WorkflowRegistry:
    workflows: dict[str, WorkflowSpec]
    test_questions: list[dict] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    base_dir: Path = PROJECT_ROOT

    # ------------------------------------------------------------------ #
    @classmethod
    def load(cls, excel_path: Path | str = DEFAULT_EXCEL,
             bindings_path: Path | str = DEFAULT_BINDINGS,
             base_dir: Path | str = PROJECT_ROOT) -> "WorkflowRegistry":
        excel_path, bindings_path = Path(excel_path), Path(bindings_path)
        rows, tests = read_excel(excel_path)
        bindings = yaml.safe_load(bindings_path.read_text(encoding="utf-8")) or {}
        wf_bindings = bindings.get("workflows", {}) or {}

        workflows: dict[str, WorkflowSpec] = {}
        for row in rows:
            wid = str(row["Workflow_ID"]).strip()
            spec = WorkflowSpec(
                id=wid,
                name=str(row["Workflow_Name"]).strip(),
                trigger=str(row["Trigger"] or "").strip(),
                inputs=str(row["Inputs"] or "").strip(),
                steps_text=[s for s in STEP_SPLIT.split(str(row["Steps"] or "").strip()) if s],
                decision_logic=str(row["Decision_Logic"] or "").strip(),
                tools_required=str(row["Tools_Required"] or "").strip(),
                expected_output=str(row["Expected_Output"] or "").strip(),
            )
            _apply_binding(spec, wf_bindings.get(wid))
            workflows[wid] = spec

        reg = cls(workflows=workflows, test_questions=tests, base_dir=Path(base_dir))
        reg.issues = reg.validate(set(wf_bindings))
        return reg

    # ------------------------------------------------------------------ #
    def get(self, workflow_id: str) -> Optional[WorkflowSpec]:
        return self.workflows.get(workflow_id)

    def executable(self, spec: WorkflowSpec) -> bool:
        return bool(spec.steps) and not any(
            i.level == "error" and i.workflow_id == spec.id for i in self.issues)

    def validate(self, bound_ids: set[str]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        tools = all_tools()
        for wid in sorted(bound_ids - set(self.workflows)):
            issues.append(ValidationIssue("warning", wid, "Binding exists but workflow is not in the Excel file (ignored)"))
        for spec in self.workflows.values():
            if not spec.steps:
                issues.append(ValidationIssue("error", spec.id, "No execution binding in workflow_bindings.yaml"))
                continue
            if len(spec.steps) != len(spec.steps_text):
                issues.append(ValidationIssue(
                    "error", spec.id,
                    f"Excel defines {len(spec.steps_text)} steps but binding has {len(spec.steps)}"))
            produced = set()
            for i, st in enumerate(spec.steps, 1):
                if st.tool not in tools:
                    issues.append(ValidationIssue("error", spec.id, f"Step {i}: unknown tool '{st.tool}'"))
                if st.output:
                    produced.add(st.output)
            if not spec.report:
                issues.append(ValidationIssue("warning", spec.id, "No report spec - raw step outputs will be shown"))
        return issues


# --------------------------------------------------------------------------- #
def read_excel(path: Path) -> tuple[list[dict], list[dict]]:
    if not path.exists():
        raise FileNotFoundError(f"Workflow Excel file not found: {path}")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = wb["Workflows"] if "Workflows" in wb.sheetnames else wb.worksheets[0]
    rows = _sheet_dicts(sheet)
    missing = [c for c in EXCEL_COLUMNS if rows and c not in rows[0]]
    if missing:
        raise ValueError(f"Workflow sheet is missing columns: {missing}")
    rows = [r for r in rows if r.get("Workflow_ID")]
    tests = _sheet_dicts(wb["Test_Questions"]) if "Test_Questions" in wb.sheetnames else []
    return rows, [t for t in tests if t.get("Workflow_ID")]


def _sheet_dicts(sheet) -> list[dict]:
    it = sheet.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(it, [])]
    return [dict(zip(header, r)) for r in it if any(c is not None for c in r)]


def _apply_binding(spec: WorkflowSpec, binding: Optional[dict]) -> None:
    if not binding:
        return
    spec.description = binding.get("description", "")
    spec.keywords = binding.get("keywords", []) or []
    spec.settings = binding.get("settings", {}) or {}
    spec.report = binding.get("report", {}) or {}
    for name, p in (binding.get("params") or {}).items():
        spec.params.append(ParamSpec(name=name, **(p or {})))
    for i, st in enumerate(binding.get("steps") or []):
        label = spec.steps_text[i] if i < len(spec.steps_text) else st.get("label", f"Step {i + 1}")
        spec.steps.append(StepBinding(
            label=label[:1].upper() + label[1:],
            tool=st["tool"],
            args=st.get("args", {}) or {},
            output=st.get("output"),
            on_error=st.get("on_error", "fail"),
            retries=int(st.get("retries", 0)),
            when=st.get("when"),
        ))
