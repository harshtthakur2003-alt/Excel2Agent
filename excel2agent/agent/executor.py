"""Generic step executor - runs ONE bound step of ANY workflow.

Responsibilities (identical for every workflow):
* resolve ``$params.x`` / ``$data.x`` / ``$settings.x`` references in step args
* evaluate an optional ``when`` condition (skip the step if false)
* call the registered tool, with retries and timing
* apply the step's error policy (``on_error: fail | continue``)
* surface decision-rule halts (needs_input / escalated) to the graph
"""
from __future__ import annotations

import time
from typing import Any

from .expressions import evaluate
from .models import Halt, StepBinding, StepOutcome, StepRecord, ToolError
from .tools import ToolContext, get_tool


def resolve(value: Any, ctx: ToolContext) -> Any:
    """Recursively replace ``$scope.path`` strings with live values."""
    if isinstance(value, str) and value.startswith("$"):
        return _lookup(value[1:], ctx)
    if isinstance(value, list):
        return [resolve(v, ctx) for v in value]
    if isinstance(value, dict):
        return {k: resolve(v, ctx) for k, v in value.items()}
    return value


def _lookup(path: str, ctx: ToolContext) -> Any:
    parts = path.split(".")
    scopes = {"params": ctx.params, "data": ctx.data, "settings": ctx.settings,
              "run_id": ctx.run_id, "request": ctx.extras.get("request", "")}
    if parts[0] not in scopes:
        return "$" + path                      # not a reference, keep literal
    cur: Any = scopes[parts[0]]
    for p in parts[1:]:
        if isinstance(cur, dict):
            cur = cur.get(p)
        elif isinstance(cur, list) and p.isdigit():
            cur = cur[int(p)] if int(p) < len(cur) else None
        else:
            return None
    return cur


def _auto_summary(value: Any) -> str:
    if isinstance(value, list):
        return f"{len(value)} record(s)"
    if isinstance(value, dict):
        return ", ".join(f"{k}: {len(v) if isinstance(v, (list, dict)) else v}"
                         for k, v in list(value.items())[:5])
    return str(value)[:120]


def run_step(index: int, step: StepBinding, ctx: ToolContext) -> tuple[StepRecord, StepOutcome | None, str | None]:
    """Execute a step. Returns (record, outcome, fatal_error_message)."""
    record = StepRecord(index=index, label=step.label, tool=step.tool, status="ok")

    if step.when:
        env = {**ctx.settings, **ctx.params, **{k: v for k, v in ctx.data.items()}}
        try:
            should_run = bool(evaluate(step.when, env))
        except Exception as exc:  # noqa: BLE001
            should_run = False
            record.error = f"condition error: {exc}"
        if not should_run:
            record.status = "skipped"
            record.summary = f"Skipped - condition not met: {step.when}"
            return record, None, None

    info = get_tool(step.tool)
    if info is None:
        record.status = "error"
        record.error = f"Unknown tool '{step.tool}'"
        return record, None, record.error

    args = resolve(step.args, ctx)
    start = time.perf_counter()
    last_error = None
    outcome: StepOutcome | None = None
    for attempt in range(1, step.retries + 2):
        record.attempts = attempt
        try:
            raw = info.func(ctx, **args)
            outcome = raw if isinstance(raw, StepOutcome) else StepOutcome(value=raw)
            last_error = None
            break
        except ToolError as exc:
            last_error = str(exc)
        except Exception as exc:  # noqa: BLE001 - unexpected bug in a tool
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt <= step.retries:
            record.decisions.append(f"Attempt {attempt} failed ({last_error}); retrying")
            time.sleep(min(0.2 * attempt, 1.0))
    record.duration_ms = round((time.perf_counter() - start) * 1000, 1)

    if last_error is not None:
        record.error = last_error
        if step.on_error == "continue":
            record.status = "error"
            record.summary = f"Failed but workflow continues (on_error=continue): {last_error}"
            if step.output:
                ctx.data[step.output] = None
            return record, None, None
        record.status = "error"
        record.summary = f"Failed: {last_error}"
        return record, None, last_error

    assert outcome is not None
    if step.output:
        ctx.data[step.output] = outcome.value
    record.summary = outcome.summary or _auto_summary(outcome.value)
    record.decisions.extend(outcome.decisions)
    if outcome.halt:
        record.status = "halted"
    return record, outcome, None


__all__ = ["run_step", "resolve", "Halt"]
