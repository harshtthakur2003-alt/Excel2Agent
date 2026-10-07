"""Edge cases: identifier normalisation, role synonyms, blank data, LLM misbehaviour."""
import json

import httpx
from openai import OpenAI

from agent import WorkflowAgent
from agent.expressions import evaluate
from agent.llm import LLMClient
from agent.tools import ToolContext
from agent.tools.duplicate_tools import compare_identifiers
from agent.tools.task_tools import _hours, _role_matches
from tests.test_llm_path import completion


def test_order_id_without_dash_is_normalised(agent):
    r = agent.run("Where is order ORD1001?")
    assert r.status == "completed" and r.report["tables"][0]["rows"][0]["order_id"] == "ORD-1001"


def test_role_synonyms_and_hours_parsing():
    assert _role_matches("Developer", "Backend Developer") and _role_matches("Developer", "software engineer")
    assert not _role_matches("Designer", "Developer")
    assert _hours("8-10 hours") == 10 and _hours(None) is None and _hours(6) == 6


def test_engineer_maps_to_developer(agent):
    r = agent.run("Assign a React and CSS bug fix task (4 hours) to an engineer")
    assert r.status == "completed" and "Rohan Das" in r.report["summary"]


def test_blank_skus_are_not_duplicates(tmp_path):
    ctx = ToolContext({}, {}, {}, tmp_path)
    rows = [{"_id": 1, "norm_sku": ""}, {"_id": 2, "norm_sku": ""}]
    assert compare_identifiers(ctx, rows).value == []


def test_missing_values_never_crash_rules():
    assert evaluate("abs(pct_diff(price, vendor_price)) > 10", {"price": 10, "vendor_price": None}) is False
    assert evaluate("'NO VENDOR PRICE' if x == None else 'ok'", {"x": None}) == "NO VENDOR PRICE"


def test_vendor_file_is_required(agent):
    r = agent.run("Process this vendor spreadsheet and show invalid rows.")
    assert r.status == "needs_input" and "attach" in r.message


def test_live_logs_missing_gives_clear_message(agent, monkeypatch, tmp_path):
    r = agent.run("Which workflows are failing most often?", {"logs_path": str(tmp_path / "none.csv")})
    assert r.status == "failed" and "No execution logs found yet" in r.message


def test_campaign_with_named_products(agent):
    r = agent.run("Create a campaign brief for SKU-1002 and SKU-1008. Goal: grow repeat purchases, 2026-11-10 to 2026-11-24")
    assert r.status == "completed"
    skus = {x["sku"] for x in next(t for t in r.report["tables"] if t["title"] == "Featured products")["rows"]}
    assert skus == {"SKU-1002", "SKU-1008"}


def test_wf004_text_only_followup(agent):
    assert agent.run("Generate SEO content for this product.").status == "needs_input"
    r = agent.run("name: Silk Scarf; category: Accessories; colour: emerald; features: hand-rolled edges, 90x90 cm")
    assert r.status == "completed" and r.params["product_name"] == "Silk Scarf"
    assert "[MISSING: material]" in r.report["sections"][0]["content"]


def _agent_with(registry, handler):
    sdk = OpenAI(api_key="t", base_url="http://fake/v1", max_retries=0,
                 http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    return WorkflowAgent(registry, LLMClient(client=sdk, offline=False), log_runs=False)


def test_llm_weird_confidence_and_incomplete_json(registry):
    def handler(request):
        body = json.loads(request.content)
        if body.get("tools"):
            name = next(t["function"]["name"] for t in body["tools"] if t["function"]["name"].startswith("WF004"))
            args = {"product_name": "Silk Scarf", "category": "Accessories", "confidence": "high", "reasoning": "x"}
            return httpx.Response(200, json=completion({"content": None, "tool_calls": [
                {"id": "c", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}))
        return httpx.Response(200, json=completion({"content": "{}"}))      # model returns nothing useful
    r = _agent_with(registry, handler).run("SEO copy for the Silk Scarf please")
    assert r.workflow_id == "WF004" and r.routing.confidence == 0.8
    assert r.status == "completed"
    assert any("filled from deterministic fallback" in d for d in r.steps[1].decisions)
