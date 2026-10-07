"""Workflow selection: offline router + generated LLM tool schemas."""
import pytest

from agent.llm import LLMClient
from agent.router import Router


@pytest.fixture
def router(registry):
    return Router(registry, LLMClient(offline=True))


def test_every_excel_test_question_routes_correctly(router, registry):
    for t in registry.test_questions:
        d = router.route(t["Test_Request"])
        assert d.workflow_id == t["Workflow_ID"], (t["Test_Request"], d.candidates)
        assert d.reasoning


@pytest.mark.parametrize("request_text,expected", [
    ("Check today's inventory and identify products that need restocking.", "WF001"),
    ("Are our prices in line with the supplier price list?", "WF002"),
    ("Clean up this vendor product file", "WF003"),
    ("Write a product description and meta description for our new boots", "WF004"),
    ("Track my order for priya.sharma@example.com", "WF005"),
    ("Do we have the same product listed twice?", "WF006"),
    ("Draft a marketing brief for the autumn launch", "WF007"),
    ("What is the search intent of my SEO keyword list?", "WF008"),
    ("Who should I give this task to? Need someone with python skills", "WF009"),
    ("Show me error rates and slow steps from the execution logs", "WF010"),
])
def test_paraphrases(router, request_text, expected):
    assert router.route(request_text).workflow_id == expected


def test_out_of_scope_request_is_rejected(router):
    assert router.route("What's the weather in Paris tomorrow?").workflow_id is None


def test_parameter_extraction(router):
    assert router.route("Where is order ORD-1001?").params["order_id"] == "ORD-1001"
    p = router.route("Which products are below 20 units and need restocking?").params
    assert p["threshold_override"] == 20
    p = router.route("Assign this urgent task to the best available developer.").params
    assert p["priority"] == "urgent" and p["role"] == "Developer"


def test_tool_schemas_generated_from_registry(router, registry):
    tools = router.tool_schemas()
    names = [t["function"]["name"] for t in tools]
    assert len(tools) == len(registry.workflows) + 1 and names[-1] == "no_matching_workflow"
    wf5 = next(t for t in tools if t["function"]["name"].startswith("WF005"))
    assert "Order ID or customer email" in wf5["function"]["description"]
    assert set(wf5["function"]["parameters"]["properties"]) >= {"order_id", "email", "confidence", "reasoning"}
