"""End-to-end runs of all 10 workflows (offline mode) with business-rule assertions."""
from pathlib import Path

import pytest
import yaml

from agent.attachments import load_attachments

CASES = yaml.safe_load(Path("examples/requests.yaml").read_text())
CASES = [c for c in CASES if c["id"] != "WF010-live-agent-logs"]   # depends on run order


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_example_case(case, agent, monkeypatch):
    for k, v in case.get("env", {}).items():
        monkeypatch.setenv(k, v)
    for turn in case["turns"]:
        r = agent.run(turn["request"], load_attachments(turn.get("attach", [])))
        assert r.status == turn["expect"], r.message
        assert r.workflow_id == case["workflow"]


def table(result, title_start):
    return next(t for t in result.report["tables"] if t["title"].startswith(title_start))


def test_wf001_threshold_rule(agent):
    r = agent.run("Which products need restocking?")
    rows = table(r, "Products requiring restock")["rows"]
    skus = {x["sku"] for x in rows}
    assert skus == {"SKU-1001", "SKU-1003", "SKU-1004", "SKU-1007", "SKU-1009", "SKU-1012"}
    assert "SKU-1006" not in skus                      # stock == minimum -> not restocked
    boots = next(x for x in rows if x["sku"] == "SKU-1004")
    assert boots["suggested_reorder_qty"] == 20        # 2*10 - 0, case pack 2
    chinos = next(x for x in rows if x["sku"] == "SKU-1003")
    assert chinos["suggested_reorder_qty"] == 36       # 50 - 18 = 32 -> rounded up to case pack 6


def test_wf002_exceptions_and_boundary(agent):
    r = agent.run("Find products where vendor price differs by more than 10%.")
    exc = {x["sku"] for x in table(r, "Exceptions")["rows"]}
    assert exc == {"SKU-1002", "SKU-1004", "SKU-1007", "SKU-1009"}
    assert "SKU-1006" not in exc                       # exactly 10% does not EXCEED 10%
    assert r.report["metrics"]["Vendor-only SKUs"] == 1


def test_wf003_invalid_rows(agent):
    r = agent.run("Process this vendor spreadsheet and show invalid rows.",
                  load_attachments(["data/vendor_files/vendor_acme_products.xlsx"]))
    invalid = table(r, "Invalid rows")["rows"]
    assert [x["_row"] for x in invalid] == [4, 5, 7]
    assert Path("outputs/files/vendor_acme_products_cleaned.csv").exists()
    assert "outputs/files/vendor_acme_products_cleaned.csv" in r.report["files"]


def test_wf004_marks_missing_never_invents(agent):
    r = agent.run("Generate SEO content for this product.",
                  load_attachments(["examples/attachments/product_wool_coat.json"]))
    text = " ".join(str(s["content"]) for s in r.report["sections"])
    assert "[MISSING: material]" in text
    seo = next(s for s in r.report["sections"] if s["title"] == "SEO title")["content"]
    meta = next(s for s in r.report["sections"] if s["title"] == "Meta description")["content"]
    assert len(seo) <= 60 and len(meta) <= 160


def test_wf005_followup_with_other_identifier(agent):
    assert agent.run("Where is order ORD-9999?").status == "needs_input"
    r = agent.run("Try priya.sharma@example.com instead")
    assert r.status == "completed"
    assert {o["order_id"] for o in table(r, "Order details")["rows"]} == {"ORD-1001", "ORD-1003"}


def test_wf006_definite_vs_possible(agent):
    r = agent.run("Find likely duplicate products in the catalog.")
    groups = {g["skus"]: g["confidence"] for g in table(r, "Duplicate groups")["rows"]}
    assert groups["JK-4001, JK-4001"] == "Definite"
    assert groups["HD-3001, HD-3007"] == "High"
    assert not any("TS-1002" in k or "JK-4002" in k or "BG-7002" in k for k in groups)   # variants / different products


def test_wf007_requires_goal_and_dates(agent):
    r = agent.run("Create a campaign brief for the new collection.")
    assert r.status == "needs_input" and "campaign goal" in r.message and "start date" in r.message


def test_wf008_dedup_and_intents(agent):
    r = agent.run("Classify these keywords and map them to pages.")
    assert r.report["metrics"] == {"Keywords read": 24, "Unique keywords": 22}
    rows = {x["keyword"]: x for x in table(r, "All keywords")["rows"]}
    assert rows["buy merino wool sweater"]["intent"] == "transactional"
    assert rows["how to wash merino wool"]["intent"] == "informational"
    assert rows["northline store login"]["intent"] == "navigational"
    assert rows["best puffer jacket 2026"]["intent"] == "commercial"


def test_wf009_picks_skilled_available_developer(agent):
    r = agent.run("Assign this urgent task to the best available developer.")
    assert r.report["sections"][0]["content"]["recommended"].startswith("Aarav Mehta")
    ranking = {x["name"]: x["status"] for x in table(r, "Candidate ranking")["rows"]}
    assert "on leave" in ranking["Meera Nair"] and "free" in ranking["Sneha Iyer"]


def test_wf010_flags(agent):
    r = agent.run("Which workflows are failing most often?")
    rows = table(r, "Workflow metrics")["rows"]
    assert rows[0]["workflow_id"] == "WF005"                    # sorted by failure rate
    flagged = {x["workflow_id"] for x in rows if x["flag"] != "OK"}
    assert {"WF005", "WF003"} <= flagged
    assert all(x["failure_rate"] <= 10 or x["flag"] != "OK" for x in rows)
