import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    """Tests are deterministic: no real OpenAI calls unless a test injects a client."""
    monkeypatch.setenv("AGENT_OFFLINE", "1")
    monkeypatch.delenv("SIMULATE_API_FAILURE", raising=False)
    from agent.services.mock_apis import reset_failures
    reset_failures()


@pytest.fixture(scope="session")
def registry():
    from agent import WorkflowRegistry
    return WorkflowRegistry.load()


@pytest.fixture
def agent(registry):
    from agent import WorkflowAgent
    from agent.llm import LLMClient
    return WorkflowAgent(registry, LLMClient(offline=True), log_runs=False)
