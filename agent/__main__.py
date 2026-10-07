"""Command-line interface.

  python -m agent "Which products need restocking?"         # one request
  python -m agent                                            # interactive chat (follow-ups supported)
  python -m agent "Generate SEO content for this product." --attach examples/attachments/product_wool_coat.json
  python -m agent list                                       # workflows loaded from Excel
  python -m agent validate                                   # cross-check Excel <-> bindings <-> tools
  python -m agent tools                                      # registered tools
  python -m agent graph                                      # print the LangGraph as Mermaid
Flags: --offline (force no-LLM mode), --json (machine-readable output)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agent", description="Excel-driven AI workflow agent")
    ap.add_argument("request", nargs="*", help="request text, or one of: list | validate | tools | graph")
    ap.add_argument("--attach", action="append", default=[],
                    help="JSON file with input data (product, campaign, task...) or a data file path (csv/xlsx)")
    ap.add_argument("--offline", action="store_true", help="do not call the LLM (deterministic fallbacks)")
    ap.add_argument("--json", action="store_true", help="print the run result as JSON")
    args = ap.parse_args(argv)
    if args.offline:
        os.environ["AGENT_OFFLINE"] = "1"

    from . import WorkflowAgent, WorkflowRegistry
    from .render import print_rich
    from .tools import all_tools
    from .attachments import load_attachments

    console = Console()
    text = " ".join(args.request).strip()

    if text in ("list", "validate", "tools", "graph"):
        reg = WorkflowRegistry.load()
        if text == "list":
            t = Table(title="Workflows loaded from Excel")
            for col in ("ID", "Name", "Trigger", "# Steps", "Executable"):
                t.add_column(col)
            for w in reg.workflows.values():
                t.add_row(w.id, w.name, w.trigger, str(len(w.steps_text)), "yes" if reg.executable(w) else "NO")
            console.print(t)
        elif text == "validate":
            if not reg.issues:
                console.print(f"[green]OK[/] - {len(reg.workflows)} workflows, every Excel step bound to a registered tool.")
            for i in reg.issues:
                console.print(f"[{'red' if i.level == 'error' else 'yellow'}]{i.level.upper()}[/] {i.workflow_id}: {i.message}")
            return 1 if any(i.level == "error" for i in reg.issues) else 0
        elif text == "tools":
            t = Table(title="Registered tools")
            for col in ("Tool", "Category", "Description"):
                t.add_column(col)
            for name, info in sorted(all_tools().items(), key=lambda x: (x[1].category, x[0])):
                t.add_row(name, info.category, info.description)
            console.print(t)
        else:
            print(WorkflowAgent(reg, log_runs=False).graph.get_graph().draw_mermaid())
        return 0

    attachments = load_attachments(args.attach)
    agent = WorkflowAgent()
    console.print(f"[dim]LLM mode: {agent.llm.mode} · {len(agent.registry.workflows)} workflows loaded from Excel[/]")

    def run(req: str, att: dict) -> None:
        result = agent.run(req, att)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            print_rich(result, console)

    if text:
        run(text, attachments)
        return 0

    console.print("[bold]Interactive mode[/] - type a request (or 'exit'). Use ':attach <file>' to attach data.")
    pending_att: dict = attachments
    while True:
        try:
            req = console.input("[bold cyan]you> [/]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if req.lower() in ("exit", "quit"):
            break
        if req.startswith(":attach "):
            pending_att.update(load_attachments([req.split(" ", 1)[1].strip()]))
            console.print(f"[dim]attached: {list(pending_att)}[/]")
            continue
        if req == ":reset":
            agent.reset()
            continue
        if req:
            run(req, pending_att)
            pending_att = {}
    return 0


if __name__ == "__main__":
    sys.exit(main())
