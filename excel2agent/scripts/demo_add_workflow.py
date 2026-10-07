"""Live demo of extensibility: adds an 11th workflow WITHOUT touching any Python code.

    python scripts/demo_add_workflow.py            # works on temporary copies (non-destructive)
    python scripts/demo_add_workflow.py --apply    # really appends WF011 to the Excel + YAML in the repo

It (1) appends a row to the Workflows sheet, (2) appends a YAML binding that re-uses existing tools,
(3) validates the registry and (4) asks the agent a plain-English question that routes to WF011.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import openpyxl  # noqa: E402
import yaml  # noqa: E402

from agent import WorkflowAgent, WorkflowRegistry  # noqa: E402
from agent.registry import DEFAULT_BINDINGS, DEFAULT_EXCEL  # noqa: E402
from agent.render import print_rich  # noqa: E402

ROW = ["WF011", "Category Stock Summary", "User asks for stock totals by product category",
       "Product inventory CSV; low-stock category threshold",
       "Load inventory → aggregate stock by category → flag low-stock categories → generate category summary",
       "Flag a category when its total stock is below 50 units", "CSV reader; calculator",
       "Stock per category with low-stock flags"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="modify the real Excel/YAML files")
    args = ap.parse_args()
    if args.apply:
        excel, bindings_path = DEFAULT_EXCEL, DEFAULT_BINDINGS
    else:
        tmp = Path(tempfile.mkdtemp())
        excel, bindings_path = tmp / "workflows.xlsx", tmp / "bindings.yaml"
        shutil.copy(DEFAULT_EXCEL, excel)
        shutil.copy(DEFAULT_BINDINGS, bindings_path)

    wb = openpyxl.load_workbook(excel)
    if not any(r[0].value == "WF011" for r in wb["Workflows"].iter_rows(min_row=2)):
        wb["Workflows"].append(ROW)
        wb.save(excel)
        snippet = (ROOT / "examples" / "wf011_extension" / "wf011_binding.yaml").read_text(encoding="utf-8")
        body = "\n".join(l for l in snippet.splitlines() if not l.startswith("#"))
        with open(bindings_path, "a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join("  " + l if l else l for l in body.splitlines()) + "\n")
    print(f"1) Excel row + 2) YAML binding added ({'repo files' if args.apply else 'temporary copies'})")

    reg = WorkflowRegistry.load(excel, bindings_path)
    print(f"3) Registry: {len(reg.workflows)} workflows, issues: {[i.message for i in reg.issues] or 'none'}")
    print("4) Asking: 'Give me stock totals by product category'\n")
    print_rich(WorkflowAgent(reg, log_runs=False).run("Give me stock totals by product category"))


if __name__ == "__main__":
    main()
