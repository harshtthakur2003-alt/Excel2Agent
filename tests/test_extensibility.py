"""Proves the architecture claim: an 11th workflow needs ZERO Python changes.

We append a row to (a copy of) the Excel file and a binding to (a copy of) the YAML
that re-uses existing tools, then ask the agent a question in plain English.
"""
import shutil

import openpyxl
import yaml

from agent import WorkflowAgent, WorkflowRegistry
from agent.llm import LLMClient
from agent.registry import DEFAULT_BINDINGS, DEFAULT_EXCEL, PROJECT_ROOT

WF011_ROW = ["WF011", "Category Stock Summary", "User asks for stock totals by product category",
             "Product inventory CSV; low-stock category threshold",
             "Load inventory → aggregate stock by category → flag low-stock categories → generate category summary",
             "Flag a category when its total stock is below 50 units", "CSV reader; calculator",
             "Stock per category with low-stock flags"]

WF011_BINDING = yaml.safe_load("""
keywords: [category, categories, stock totals, summary]
settings: {category_threshold: 50}
steps:
  - tool: load_table
    args: {path: data/inventory.csv}
    output: inventory
  - tool: aggregate
    args: {rows: $data.inventory, group_by: [category],
           metrics: {total_stock: {op: sum, field: current_stock}, products: {op: count}}}
    output: by_category
  - tool: compute_columns
    args: {rows: $data.by_category, variables: {limit: $settings.category_threshold},
           columns: {low_stock: total_stock < limit}}
    output: flagged
  - tool: filter_rows
    args: {rows: $data.flagged, condition: low_stock, label: categories}
    output: low
report:
  title: Category stock summary
  vars: {low: $data.low}
  computed: {n: len(low)}
  summary: "{n} category(ies) below the threshold."
  tables:
    - {title: Stock by category, rows: $data.flagged, columns: [category, products, total_stock, low_stock]}
""")


def test_eleventh_workflow_without_code_changes(tmp_path):
    excel = tmp_path / "workflows.xlsx"
    shutil.copy(DEFAULT_EXCEL, excel)
    wb = openpyxl.load_workbook(excel)
    wb["Workflows"].append(WF011_ROW)
    wb.save(excel)

    bindings = yaml.safe_load(DEFAULT_BINDINGS.read_text())
    bindings["workflows"]["WF011"] = WF011_BINDING
    bpath = tmp_path / "bindings.yaml"
    bpath.write_text(yaml.safe_dump(bindings, sort_keys=False))

    reg = WorkflowRegistry.load(excel, bpath, base_dir=PROJECT_ROOT)
    assert not [i for i in reg.issues if i.level == "error"]
    agent = WorkflowAgent(reg, LLMClient(offline=True), log_runs=False)

    r = agent.run("Give me stock totals by product category")
    assert r.workflow_id == "WF011" and r.status == "completed"
    assert [s.label for s in r.steps][0] == "Load inventory"
    rows = {x["category"]: x for x in r.report["tables"][0]["rows"]}
    assert rows["Footwear"]["total_stock"] == 42 and rows["Footwear"]["low_stock"] is True
    # the original ten still route correctly with the new workflow present
    assert agent.run("Which products need restocking?").workflow_id == "WF001"
