"""LangGraph orchestration - the same 4-node graph runs every workflow.

    START -> route_request --(no match)--------------------------> finalize -> END
                   |
                   v
             load_workflow --(not executable)--------------------> finalize
                   |
                   v
             execute_step <-- loop while steps remain and status == running
                   |
                   v
               finalize   (build declarative report, set status, remember follow-ups)

Adding an 11th workflow never touches this file.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict
from typing import Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .executor import resolve, run_step
from .llm import LLMClient
from .models import RoutingDecision, RunResult, StepRecord
from .registry import WorkflowRegistry
from .router import Router
from .run_logger import RunLogger
from .tools import ToolContext, get_tool


class AgentState(TypedDict, total=False):
    request: str
    context_request: str   # original request + follow-up answers (for multi-turn workflows)
    attachments: dict
    pending: Optional[dict]
    run_id: str
    routing: Optional[RoutingDecision]
    workflow_id: Optional[str]
    params: dict
    data: dict
    step_index: int
    steps: list
    status: str            # running | completed | needs_input | escalated | failed | no_match
    message: str
    report: Optional[dict]
    missing: list


class WorkflowAgent:
    """User request -> Agent -> Identify workflow -> Steps -> Tools -> Decisions -> Result."""

    def __init__(self, registry: Optional[WorkflowRegistry] = None, llm: Optional[LLMClient] = None,
                 log_runs: bool = True):
        self.registry = registry or WorkflowRegistry.load()
        self.llm = llm or LLMClient()
        self.router = Router(self.registry, self.llm)
        self.logger = RunLogger(self.registry.base_dir) if log_runs else None
        self.pending: Optional[dict] = None          # conversational memory for follow-up questions
        self.graph = self._build_graph()

    # ------------------------------------------------------------------ #
    def run(self, request: str, attachments: Optional[dict] = None) -> RunResult:
        t0 = time.perf_counter()
        state: AgentState = {
            "request": request, "attachments": attachments or {}, "pending": self.pending,
            "run_id": f"run-{uuid.uuid4().hex[:8]}", "data": {}, "steps": [], "step_index": 0,
            "status": "running", "message": "", "report": None, "params": {}, "missing": [],
        }
        final = self.graph.invoke(state, {"recursion_limit": 200})
        spec = self.registry.get(final.get("workflow_id") or "")
        result = RunResult(
            request=request, status=final["status"], routing=final.get("routing"),
            workflow_id=spec.id if spec else None, workflow_name=spec.name if spec else None,
            params=final.get("params", {}), steps=final.get("steps", []), report=final.get("report"),
            message=final.get("message", ""), run_id=final["run_id"], llm_mode=self.llm.mode,
            total_ms=round((time.perf_counter() - t0) * 1000, 1),
        )
        # remember an unanswered question so the next message can complete it
        self.pending = ({"workflow_id": result.workflow_id, "params": result.params,
                         "request": final.get("context_request") or request,
                         "message": result.message, "missing": final.get("missing", [])}
                        if result.status == "needs_input" and result.workflow_id else None)
        if self.logger:
            self.logger.log(result)
        return result

    def reset(self) -> None:
        self.pending = None

    # ------------------------------------------------------------------ #
    # Graph
    # ------------------------------------------------------------------ #
    def _build_graph(self):
        g = StateGraph(AgentState)
        g.add_node("route_request", self._route_node)
        g.add_node("load_workflow", self._load_node)
        g.add_node("execute_step", self._execute_node)
        g.add_node("finalize", self._finalize_node)
        g.add_edge(START, "route_request")
        g.add_conditional_edges("route_request", lambda s: "load_workflow" if s.get("workflow_id") else "finalize",
                                ["load_workflow", "finalize"])
        g.add_conditional_edges("load_workflow", lambda s: "execute_step" if s["status"] == "running" else "finalize",
                                ["execute_step", "finalize"])
        g.add_conditional_edges("execute_step", self._next_after_step, ["execute_step", "finalize"])
        g.add_edge("finalize", END)
        return g.compile()

    def _route_node(self, s: AgentState) -> dict:
        decision = self.router.route(s["request"], s.get("attachments"), s.get("pending"))
        if not decision.workflow_id:
            names = ", ".join(w.name for w in self.registry.workflows.values())
            return {"routing": decision, "workflow_id": None, "status": "no_match",
                    "message": f"I couldn't match this request to a workflow. {decision.reasoning} "
                               f"Available workflows: {names}."}
        pending = s.get("pending")
        context = s["request"]
        if pending and pending.get("workflow_id") == decision.workflow_id:
            context = f"{pending.get('request', '')}\n{s['request']}"
        return {"routing": decision, "workflow_id": decision.workflow_id, "params": decision.params,
                "context_request": context}

    def _load_node(self, s: AgentState) -> dict:
        spec = self.registry.get(s["workflow_id"])
        if not self.registry.executable(spec):
            errs = [i.message for i in self.registry.issues if i.workflow_id == spec.id]
            return {"status": "failed", "message": f"Workflow '{spec.name}' is defined in Excel but not executable: {errs}"}
        return {"status": "running", "step_index": 0}

    def _ctx(self, s: AgentState) -> ToolContext:
        spec = self.registry.get(s["workflow_id"])
        return ToolContext(params=s.get("params", {}), settings=spec.settings, data=s["data"],
                           base_dir=self.registry.base_dir, llm=self.llm, workflow=spec, run_id=s["run_id"],
                           extras={"request": s.get("context_request") or s["request"]})

    def _execute_node(self, s: AgentState) -> dict:
        spec = self.registry.get(s["workflow_id"])
        idx = s["step_index"]
        ctx = self._ctx(s)
        record, outcome, fatal = run_step(idx + 1, spec.steps[idx], ctx)
        update: dict[str, Any] = {"steps": s["steps"] + [record], "step_index": idx + 1, "data": ctx.data}
        if fatal:
            update.update(status="failed",
                          message=f"Step {idx + 1} '{record.label}' failed: {fatal}")
        elif outcome and outcome.halt:
            update.update(status=outcome.halt.status, message=outcome.halt.message,
                          missing=outcome.halt.missing)
        elif outcome and outcome.run_status:
            update["data"] = {**ctx.data, "_run_status": outcome.run_status}
        return update

    def _next_after_step(self, s: AgentState) -> str:
        spec = self.registry.get(s["workflow_id"])
        if s["status"] == "running" and s["step_index"] < len(spec.steps):
            return "execute_step"
        return "finalize"

    def _finalize_node(self, s: AgentState) -> dict:
        if s["status"] != "running":
            return {}
        spec = self.registry.get(s["workflow_id"])
        status = s["data"].get("_run_status", "completed")
        report = None
        if spec.report:
            ctx = self._ctx(s)
            try:
                report = get_tool("build_report").func(ctx, **resolve(spec.report, ctx)).value
            except Exception as exc:  # noqa: BLE001
                return {"status": "failed", "message": f"Report generation failed: {exc}"}
        else:
            report = {"title": spec.name, "summary": "", "raw": {k: v for k, v in s["data"].items()}}
        return {"status": status, "report": report, "message": report.get("summary", "")}


def result_steps_as_dicts(steps: list[StepRecord]) -> list[dict]:
    return [asdict(x) for x in steps]
