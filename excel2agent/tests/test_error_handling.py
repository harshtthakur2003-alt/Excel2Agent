"""Conditions, retries, error policies and expression safety."""
import pytest

from agent.expressions import ExpressionError, evaluate
from agent.models import StepBinding
from agent.executor import run_step
from agent.tools import ToolContext


def test_transient_api_error_is_retried(agent, monkeypatch):
    monkeypatch.setenv("SIMULATE_API_FAILURE", "order_api:2")
    r = agent.run("Where is order ORD-1001?")
    assert r.status == "completed"
    assert r.steps[1].attempts == 3


def test_persistent_api_error_fails_cleanly(agent, monkeypatch):
    monkeypatch.setenv("SIMULATE_API_FAILURE", "order_api")
    r = agent.run("Where is order ORD-1001?")
    assert r.status == "failed" and "Search order data" in r.message
    assert len(r.steps) == 2                             # stopped at the failing step


def test_shipment_api_down_degrades_gracefully(agent, monkeypatch):
    monkeypatch.setenv("SIMULATE_API_FAILURE", "shipment_api")
    r = agent.run("Where is order ORD-1001?")
    assert r.status == "completed"
    assert "unavailable" in str(r.report["sections"][0]["content"])


def test_missing_file_fails_with_message(agent):
    r = agent.run("Process this vendor spreadsheet", {"file_path": "data/nope.xlsx"})
    assert r.status == "failed" and "File not found" in r.message


def test_invalid_identifier_asks_user(agent):
    r = agent.run("Where is my order?")
    assert r.status == "needs_input" and "order ID" in r.message


def _ctx(tmp_path):
    return ToolContext(params={}, settings={}, data={"rows": [{"a": 1}]}, base_dir=tmp_path)


def test_on_error_continue_policy(tmp_path):
    step = StepBinding(label="x", tool="load_table", args={"path": "missing.csv"}, output="t", on_error="continue")
    rec, outcome, fatal = run_step(1, step, _ctx(tmp_path))
    assert fatal is None and rec.status == "error"


def test_when_condition_skips_step(tmp_path):
    step = StepBinding(label="x", tool="filter_rows", args={"rows": "$data.rows", "condition": "a > 0"}, when="False")
    rec, _, _ = run_step(1, step, _ctx(tmp_path))
    assert rec.status == "skipped"


@pytest.mark.parametrize("expr", ["__import__('os')", "a.__class__", "open('x')", "(lambda: 1)()"])
def test_expressions_are_sandboxed(expr):
    with pytest.raises(ExpressionError):
        evaluate(expr, {"a": 1})


def test_expression_semantics():
    assert evaluate("current_stock < minimum_stock", {"current_stock": "4", "minimum_stock": 20}) is True
    assert evaluate("abs(pct_diff(55, 50)) > 10", {}) is False
    assert evaluate("ceil_to(32, 6)", {}) == 36
    assert evaluate("x > 1", {"x": None}) is False
