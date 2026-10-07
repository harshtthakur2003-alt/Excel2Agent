"""The Excel file is the source of truth and is cross-validated against the bindings."""
from agent.registry import read_excel, DEFAULT_EXCEL
from agent.tools import all_tools


def test_loads_all_ten_workflows_from_excel(registry):
    assert list(registry.workflows) == [f"WF{i:03d}" for i in range(1, 11)]


def test_no_validation_issues(registry):
    assert [i for i in registry.issues if i.level == "error"] == []


def test_every_excel_step_is_bound_in_order(registry):
    rows, _ = read_excel(DEFAULT_EXCEL)
    for row in rows:
        spec = registry.get(row["Workflow_ID"])
        excel_steps = [s.strip() for s in row["Steps"].split("→")]
        assert len(spec.steps) == len(excel_steps)
        for bound, text in zip(spec.steps, excel_steps):
            assert bound.label.lower() == text.lower()      # labels come from Excel, not code
            assert bound.tool in all_tools()


def test_excel_fields_are_carried_through(registry):
    wf = registry.get("WF001")
    assert wf.decision_logic.startswith("If current_stock < minimum_stock")
    assert "CSV reader" in wf.tools_required
    assert len(registry.test_questions) == 10


def test_missing_binding_is_reported(tmp_path):
    import yaml
    from agent import WorkflowRegistry
    from agent.registry import DEFAULT_BINDINGS
    b = yaml.safe_load(DEFAULT_BINDINGS.read_text())
    del b["workflows"]["WF006"]
    b["workflows"]["WF001"]["steps"][0]["tool"] = "does_not_exist"
    p = tmp_path / "b.yaml"
    p.write_text(yaml.safe_dump(b))
    reg = WorkflowRegistry.load(bindings_path=p)
    msgs = {(i.workflow_id, i.message) for i in reg.issues}
    assert ("WF006", "No execution binding in workflow_bindings.yaml") in msgs
    assert any(w == "WF001" and "unknown tool" in m for w, m in msgs)
    assert not reg.executable(reg.get("WF006"))
