"""WF010 Workflow Performance Report - run roll-up, error and latency analysis."""
from __future__ import annotations

from collections import Counter, defaultdict

from ..models import StepOutcome
from . import ToolContext, register_tool

ERROR_PLAYBOOK = [
    ("timeout", "Add retries with exponential backoff and a circuit breaker; review the upstream API's SLA/timeout."),
    ("503", "Upstream service unavailable - add retries/backoff and an alert on the dependency's health."),
    ("rate limit", "Throttle LLM calls: batch requests, add backoff on 429, or raise the rate-limit tier."),
    ("invalid json", "Use JSON mode / schema validation and re-ask the model on parse errors."),
    ("encoding", "Detect file encoding (e.g. UTF-8 vs Latin-1) before parsing vendor files."),
    ("header", "Validate the header row up-front and return a clear message to the vendor."),
    ("connection reset", "Use connection pooling and retry transient DB errors."),
]


def _runs(logs: list) -> dict:
    runs: dict = defaultdict(lambda: {"failed": False, "duration": 0.0, "workflow_id": None, "workflow_name": None})
    for r in logs:
        run = runs[r["run_id"]]
        run["workflow_id"], run["workflow_name"] = r["workflow_id"], r["workflow_name"]
        run["duration"] += float(r["duration_ms"] or 0)
        if str(r["status"]).lower() != "success":
            run["failed"] = True
    return runs


@register_tool("workflow_success_rates", "calculator", "Success / failure rate per workflow (run level)")
def workflow_success_rates(ctx: ToolContext, logs: list) -> StepOutcome:
    stats: dict = {}
    for rid, run in _runs(logs).items():
        s = stats.setdefault(run["workflow_id"], {"workflow_id": run["workflow_id"], "workflow_name": run["workflow_name"],
                                                  "runs": 0, "failed_runs": 0})
        s["runs"] += 1
        s["failed_runs"] += run["failed"]
    for s in stats.values():
        s["success_rate"] = round(100 * (s["runs"] - s["failed_runs"]) / s["runs"], 1)
        s["failure_rate"] = round(100 * s["failed_runs"] / s["runs"], 1)
    out = sorted(stats.values(), key=lambda s: -s["failure_rate"])
    total = sum(s["runs"] for s in out)
    failed = sum(s["failed_runs"] for s in out)
    return StepOutcome(out, f"{total} runs across {len(out)} workflows; overall failure rate {100 * failed / max(total, 1):.1f}%")


@register_tool("average_execution_time", "calculator", "Average end-to-end run time per workflow")
def average_execution_time(ctx: ToolContext, logs: list, stats: list) -> StepOutcome:
    durations: dict = defaultdict(list)
    for run in _runs(logs).values():
        durations[run["workflow_id"]].append(run["duration"])
    out = []
    for s in stats:
        d = durations[s["workflow_id"]]
        out.append({**s, "avg_run_ms": round(sum(d) / len(d)), "max_run_ms": round(max(d))})
    return StepOutcome(out, "Slowest: " + ", ".join(f"{s['workflow_id']} {s['avg_run_ms']}ms" for s in
                                                   sorted(out, key=lambda s: -s["avg_run_ms"])[:3]))


@register_tool("frequent_errors", "reporting", "Most frequent error messages")
def frequent_errors(ctx: ToolContext, logs: list, top_n: int = 5) -> StepOutcome:
    c = Counter((r["workflow_id"], r["step_name"], r["error_message"]) for r in logs if r.get("error_message"))
    total = sum(c.values()) or 1
    out = [{"workflow_id": w, "step_name": s, "error_message": e, "occurrences": n, "share_of_errors": f"{100 * n / total:.0f}%"}
           for (w, s, e), n in c.most_common(top_n)]
    return StepOutcome(out, f"{sum(c.values())} errors; top: {out[0]['error_message'] if out else 'none'}")


@register_tool("slow_steps", "calculator", "Steps whose average duration exceeds the threshold")
def slow_steps(ctx: ToolContext, logs: list, threshold_ms: float) -> StepOutcome:
    d: dict = defaultdict(list)
    for r in logs:
        if str(r["status"]).lower() == "success":         # exclude timeouts so they don't mask latency
            d[(r["workflow_id"], r["step_name"])].append(float(r["duration_ms"] or 0))
    out = [{"workflow_id": w, "step_name": s, "avg_ms": round(sum(v) / len(v)), "executions": len(v)}
           for (w, s), v in d.items() if sum(v) / len(v) > threshold_ms]
    out.sort(key=lambda x: -x["avg_ms"])
    return StepOutcome(out, f"{len(out)} step(s) average above {threshold_ms:.0f}ms",
                       decisions=[f"Slow step rule: avg successful duration > {threshold_ms:.0f}ms"])


@register_tool("performance_recommendations", "reporting", "Flag problem workflows and recommend fixes")
def performance_recommendations(ctx: ToolContext, stats: list, errors: list, slow: list,
                                failure_threshold: float, time_threshold_ms: float) -> StepOutcome:
    flagged, recs = [], []
    for s in stats:
        reasons = []
        if s["failure_rate"] > failure_threshold:
            reasons.append(f"failure rate {s['failure_rate']}% > {failure_threshold:g}%")
        if s["avg_run_ms"] > time_threshold_ms:
            reasons.append(f"avg time {s['avg_run_ms']}ms > {time_threshold_ms:.0f}ms")
        s["flag"] = "⚠ " + "; ".join(reasons) if reasons else "OK"
        if reasons:
            flagged.append(s)
    mentioned = set()
    for s in flagged:
        errs = [e for e in errors if e["workflow_id"] == s["workflow_id"]]
        if errs:
            e = errs[0]
            fix = next((f for k, f in ERROR_PLAYBOOK if k in e["error_message"].lower()), "Investigate root cause in logs.")
            recs.append(f"{s['workflow_id']} {s['workflow_name']}: most common error '{e['error_message']}' in step "
                        f"'{e['step_name']}' -> {fix}")
        if s["avg_run_ms"] > time_threshold_ms:
            st = [x for x in slow if x["workflow_id"] == s["workflow_id"]]
            if st:
                mentioned.add((st[0]["workflow_id"], st[0]["step_name"]))
                recs.append(f"{s['workflow_id']} {s['workflow_name']}: slow step '{st[0]['step_name']}' "
                            f"({st[0]['avg_ms']}ms avg) -> cache results, parallelise or use a smaller/faster model.")
    for x in slow:
        if (x["workflow_id"], x["step_name"]) not in mentioned:
            recs.append(f"{x['workflow_id']}: step '{x['step_name']}' averages {x['avg_ms']}ms - watch it "
                        "(above the per-step threshold) - consider caching, batching or a faster model.")
    if not recs:
        recs.append("All workflows are within thresholds - no action needed.")
    return StepOutcome({"flagged": flagged, "recommendations": recs, "stats": stats},
                       f"{len(flagged)} workflow(s) flagged; {len(recs)} recommendation(s)",
                       decisions=[f"Flag rule: failure rate > {failure_threshold:g}% OR avg time > {time_threshold_ms:.0f}ms"])
