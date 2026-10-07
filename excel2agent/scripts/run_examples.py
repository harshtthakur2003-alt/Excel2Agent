"""Runs every case in examples/requests.yaml and writes the results to outputs/.

    python scripts/run_examples.py            # uses OpenAI if OPENAI_API_KEY is set
    python scripts/run_examples.py --offline  # deterministic fallbacks only

Outputs:
    outputs/results.md              all runs, human readable (selected workflow, steps, result)
    outputs/results.json            all runs, machine readable
    outputs/by_workflow/WF00X.md    one file per workflow
    outputs/files/*.csv             files produced by workflows (restock list, cleaned vendor file, ...)
Exit code is non-zero if any run's status differs from the expected status.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--only", help="run only cases whose id starts with this prefix")
    args = ap.parse_args()
    if args.offline:
        os.environ["AGENT_OFFLINE"] = "1"

    import yaml
    from agent import WorkflowAgent, WorkflowRegistry
    from agent.attachments import load_attachments
    from agent.llm import LLMClient
    from agent.render import to_markdown
    from agent.services.mock_apis import reset_failures

    cases = yaml.safe_load((ROOT / "examples" / "requests.yaml").read_text(encoding="utf-8"))
    if args.only:
        cases = [c for c in cases if c["id"].startswith(args.only)]
    if not args.only:
        shutil.rmtree(ROOT / "logs", ignore_errors=True)        # fresh live log for the WF010-live case

    registry = WorkflowRegistry.load()
    llm = LLMClient()
    md = [f"# Example runs\n\nGenerated {datetime.now():%Y-%m-%d %H:%M} · LLM mode: `{llm.mode}` · "
          f"{len(registry.workflows)} workflows loaded from Excel\n"]
    by_wf: dict[str, list[str]] = {}
    all_json, failures, rows = [], [], []

    for case in cases:
        saved_env = {k: os.environ.get(k) for k in case.get("env", {})}
        os.environ.update(case.get("env", {}))
        reset_failures()
        agent = WorkflowAgent(registry, llm)              # fresh conversation per case
        section = [f"\n---\n## {case['id']}\n"]
        for turn_no, turn in enumerate(case["turns"], 1):
            result = agent.run(turn["request"], load_attachments(turn.get("attach", [])))
            ok = result.status == turn["expect"] and (case["workflow"] is None or result.workflow_id == case["workflow"])
            if not ok:
                failures.append(f"{case['id']} turn {turn_no}: got {result.status}/{result.workflow_id}, "
                                f"expected {turn['expect']}/{case['workflow']}")
            label = f"Turn {turn_no}" if len(case["turns"]) > 1 else ""
            if case.get("env"):
                section.append(f"_Environment: `{case['env']}`_\n")
            if turn.get("attach"):
                section.append(f"_Attachments: {', '.join(turn['attach'])}_\n")
            section.append((f"#### {label}\n" if label else "") + to_markdown(result))
            all_json.append({"case": case["id"], "turn": turn_no, "expected": turn["expect"], **result.to_dict()})
            rows.append((case["id"], turn_no, result.workflow_id or "-", result.status, turn["expect"], "✅" if ok else "❌"))
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        md.extend(section)
        by_wf.setdefault(case["workflow"] or "no_match", []).extend(section)

    summary = ["\n## Summary\n", "| Case | Turn | Workflow | Status | Expected | OK |", "|---|---|---|---|---|---|"]
    summary += [f"| {a} | {b} | {c} | {d} | {e} | {f} |" for a, b, c, d, e, f in rows]
    md[1:1] = summary
    out = ROOT / "outputs"
    (out / "by_workflow").mkdir(parents=True, exist_ok=True)
    (out / "results.md").write_text("\n".join(md), encoding="utf-8")
    (out / "results.json").write_text(json.dumps(all_json, indent=2, default=str), encoding="utf-8")
    for wid, sec in by_wf.items():
        spec = registry.get(wid)
        title = f"# {wid} - {spec.name}\n" if spec else "# Requests with no matching workflow\n"
        (out / "by_workflow" / f"{wid}.md").write_text(title + "\n".join(sec), encoding="utf-8")

    print("\n".join(f"{'OK ' if r[5] == '✅' else 'BAD'} {r[0]:<36} turn {r[1]}  {r[2]:<6} {r[3]:<12} (expected {r[4]})"
                    for r in rows))
    print(f"\n{len(rows) - len(failures)}/{len(rows)} runs as expected. Results written to outputs/results.md")
    for f in failures:
        print("MISMATCH:", f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
