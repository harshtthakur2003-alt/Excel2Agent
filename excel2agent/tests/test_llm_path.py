"""Exercises the OpenAI code path with the REAL openai SDK against a mocked HTTP transport.

No network or API key needed: we verify that tool-calling routing, JSON-mode generation,
text validation/retry and fallbacks work end-to-end through the SDK's request/response parsing.
"""
import json

import httpx
import pytest
from openai import OpenAI

from agent import WorkflowAgent
from agent.llm import LLMClient


def completion(message: dict) -> dict:
    return {"id": "chatcmpl-test", "object": "chat.completion", "created": 0, "model": "gpt-test",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", **message}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}


class FakeLLMServer:
    """Plays the role of the OpenAI API. Records requests for assertions."""

    def __init__(self, route_to: str, route_args: dict, too_long_first: bool = False, fail_json: bool = False):
        self.route_to, self.route_args = route_to, route_args
        self.too_long_first, self.fail_json = too_long_first, fail_json
        self.requests: list[dict] = []
        self.json_calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append(body)
        if body.get("tools"):                               # routing call
            name = next(t["function"]["name"] for t in body["tools"] if t["function"]["name"].startswith(self.route_to))
            args = {**self.route_args, "confidence": 0.93, "reasoning": "Matches the trigger of " + self.route_to}
            return httpx.Response(200, json=completion({"content": None, "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}))
        self.json_calls += 1
        if self.fail_json:
            return httpx.Response(500, json={"error": {"message": "boom"}})
        user = body["messages"][-1]["content"]
        keys = json.loads(user.split("Return JSON with exactly these keys: ")[1].split("\n")[0])
        long = self.too_long_first and self.json_calls == 1
        out = {k: ("x " * 500 if long else f"Generated {k} from given facts only") for k in keys}
        return httpx.Response(200, json=completion({"content": json.dumps(out)}))


def make_agent(registry, server):
    sdk = OpenAI(api_key="test", base_url="http://fake/v1", max_retries=0,
                 http_client=httpx.Client(transport=httpx.MockTransport(server)))
    return WorkflowAgent(registry, LLMClient(model="gpt-test", client=sdk, offline=False), log_runs=False)


def test_llm_tool_calling_routes_and_extracts_params(registry):
    server = FakeLLMServer("WF005", {"order_id": "ORD-1002"})
    r = make_agent(registry, server).run("hey, any news on my boots? order ORD-1002")
    assert r.routing.method == "llm-tool-calling" and r.routing.confidence == 0.93
    assert r.workflow_id == "WF005" and r.params["order_id"] == "ORD-1002" and r.status == "completed"
    sent = server.requests[0]
    assert sent["tool_choice"] == "required" and len(sent["tools"]) == 11


def test_llm_generation_with_validation_retry(registry):
    server = FakeLLMServer("WF004", {"product_name": "Silk Scarf", "category": "Accessories", "color": "emerald"},
                           too_long_first=True)
    r = make_agent(registry, server).run("Write SEO copy for our emerald Silk Scarf (Accessories)")
    assert r.status == "completed"
    desc_step = r.steps[1]
    assert any("Text validation failed" in d for d in desc_step.decisions)   # model asked to fix
    assert any("Generated with openai:gpt-test" in d for d in desc_step.decisions)
    assert "missing_fields" in server.requests[1]["messages"][1]["content"]   # grounding info sent
    assert r.report["sections"][0]["content"].startswith("Generated description")


def test_llm_failure_falls_back_to_template(registry):
    server = FakeLLMServer("WF004", {"product_name": "Silk Scarf", "category": "Accessories"}, fail_json=True)
    r = make_agent(registry, server).run("Write SEO copy for the Silk Scarf")
    assert r.status == "completed"
    assert any("fallback" in d for d in r.steps[1].decisions)
    assert "[MISSING: material]" in r.report["sections"][0]["content"]


def test_routing_falls_back_offline_when_api_errors(registry):
    def broken(request):
        return httpx.Response(500, json={"error": {"message": "down"}})
    sdk = OpenAI(api_key="t", base_url="http://fake/v1", max_retries=0,
                 http_client=httpx.Client(transport=httpx.MockTransport(broken)))
    agent = WorkflowAgent(registry, LLMClient(client=sdk, offline=False), log_runs=False)
    r = agent.run("Which products need restocking?")
    assert r.workflow_id == "WF001" and "offline router" in r.routing.reasoning
