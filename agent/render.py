"""Presentation of a RunResult: rich console output and Markdown (for outputs/ and the UI)."""
from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import RunResult

STATUS_STYLE = {"completed": "green", "needs_input": "yellow", "escalated": "magenta",
                "failed": "red", "no_match": "red"}
STEP_ICON = {"ok": "✔", "skipped": "↷", "error": "✘", "halted": "⏸"}


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(f"- {_content_to_text(c) if not isinstance(c, dict) else _inline(c)}" for c in content)
    if isinstance(content, dict):
        return "\n".join(f"- **{k.replace('_', ' ')}**: {_inline(v)}" for k, v in content.items())
    return str(content)


def _inline(v: Any) -> str:
    if isinstance(v, list):
        if v and isinstance(v[0], dict):
            return "; ".join(", ".join(f"{k}={x}" for k, x in d.items()) for d in v)
        return "; ".join(map(str, v))
    if isinstance(v, dict):
        return ", ".join(f"{k}: {x}" for k, x in v.items())
    return str(v)


# --------------------------------------------------------------------------- #
def to_markdown(r: RunResult, parts: tuple = ("header", "steps", "report")) -> str:
    out: list[str] = []
    if "header" in parts:
        out += _md_header(r)
    if "steps" in parts:
        out += _md_steps(r)
    if "report" in parts:
        out += _md_report(r)
    return "\n".join(out) + "\n"


def _md_header(r: RunResult) -> list[str]:
    out = [f"### Request\n> {r.request}\n"]
    rt = r.routing
    if r.workflow_id:
        out.append(f"**Selected workflow:** `{r.workflow_id}` - {r.workflow_name}  ")
    else:
        out.append("**Selected workflow:** none  ")
    if rt:
        out.append(f"**Routing:** {rt.method}, confidence {rt.confidence:.2f} - {rt.reasoning}  ")
    out.append(f"**Status:** `{r.status.upper()}` · LLM mode: `{r.llm_mode}` · {r.total_ms:.0f} ms  ")
    shown = {k: v for k, v in r.params.items() if v not in (None, "", [])}
    if shown:
        out.append(f"**Extracted parameters:** `{json.dumps(shown, default=str)}`\n")
    return out


def _md_steps(r: RunResult) -> list[str]:
    out: list[str] = []
    if r.steps:
        out.append("\n**Steps executed:**\n")
        for s in r.steps:
            line = f"{s.index}. {STEP_ICON.get(s.status, '?')} **{s.label}** (`{s.tool}`, {s.duration_ms:.0f} ms) - {s.summary}"
            if s.attempts > 1:
                line += f" _(attempts: {s.attempts})_"
            out.append(line)
            for d in s.decisions:
                out.append(f"    - ↳ {d}")
    out.append("")
    return out


def _md_report(r: RunResult) -> list[str]:
    out: list[str] = []
    if r.status in ("needs_input", "failed", "no_match"):
        label = {"needs_input": "Agent needs more information", "failed": "Workflow failed",
                 "no_match": "No workflow selected"}[r.status]
        out.append(f"**{label}:** {r.message}\n")
    rep = r.report
    if rep:
        out.append(f"#### Result: {rep['title']}")
        if r.status == "escalated":
            out.append("> **ESCALATED** - no suitable employee found; manager decision required.\n")
        if rep.get("summary"):
            out.append(rep["summary"] + "\n")
        if rep.get("metrics"):
            out.append(" · ".join(f"**{k}:** {v}" for k, v in rep["metrics"].items()) + "\n")
        for sec in rep.get("sections", []):
            out.append(f"**{sec['title']}**\n\n{_content_to_text(sec['content'])}\n")
        for t in rep.get("tables", []):
            out.append(f"**{t['title']}**\n")
            if not t["rows"]:
                out.append(f"_{t['empty_message']}_\n")
                continue
            out.append("| " + " | ".join(map(str, t["headers"])) + " |")
            out.append("|" + "---|" * len(t["headers"]))
            for row in t["rows"]:
                out.append("| " + " | ".join(str(row.get(c, "")).replace("|", "/") for c in t["columns"]) + " |")
            out.append("")
        for n in rep.get("notes", []):
            out.append(f"> {n}  ")
        if rep.get("files"):
            out.append("\nFiles written: " + ", ".join(f"`{f}`" for f in rep["files"]))
    return out


# --------------------------------------------------------------------------- #
def print_rich(r: RunResult, console: Console | None = None) -> None:
    c = console or Console()
    rt = r.routing
    head = (f"[bold]Selected workflow:[/] {r.workflow_id or '-'}  {r.workflow_name or ''}\n"
            + (f"[bold]Routing:[/] {rt.method} · confidence {rt.confidence:.2f}\n[dim]{rt.reasoning}[/]\n" if rt else "")
            + f"[bold]Status:[/] [{STATUS_STYLE.get(r.status, 'white')}]{r.status.upper()}[/] · LLM: {r.llm_mode} · {r.total_ms:.0f} ms")
    shown = {k: v for k, v in r.params.items() if v not in (None, "", [])}
    if shown:
        head += f"\n[bold]Parameters:[/] {json.dumps(shown, default=str)[:300]}"
    c.print(Panel(head, title=f"[bold]{r.request}[/]", border_style="cyan"))

    if r.steps:
        t = Table(title="Steps executed", show_lines=False, expand=True)
        for col in ("#", "Step (from Excel)", "Tool", "Status", "ms", "Result / decisions"):
            t.add_column(col, overflow="fold")
        for s in r.steps:
            detail = s.summary + ("".join(f"\n↳ {d}" for d in s.decisions))
            style = {"ok": "green", "error": "red", "halted": "yellow", "skipped": "dim"}.get(s.status)
            t.add_row(str(s.index), s.label, s.tool, f"[{style}]{STEP_ICON.get(s.status)} {s.status}[/]",
                      f"{s.duration_ms:.0f}", detail)
        c.print(t)

    if r.status in ("needs_input", "failed", "no_match"):
        c.print(Panel(r.message, title=r.status.replace("_", " ").upper(), border_style=STATUS_STYLE[r.status]))
    rep = r.report
    if not rep:
        return
    body = rep.get("summary", "")
    if rep.get("metrics"):
        body += "\n" + "  ·  ".join(f"[bold]{k}:[/] {v}" for k, v in rep["metrics"].items())
    if r.status == "escalated":
        body = "[bold magenta]ESCALATED - manager decision required[/]\n" + body
    c.print(Panel(body, title=f"[bold]Result: {rep['title']}[/]", border_style=STATUS_STYLE.get(r.status, "green")))
    for sec in rep.get("sections", []):
        c.print(f"[bold underline]{sec['title']}[/]")
        c.print(_content_to_text(sec["content"]).replace("**", ""))
        c.print()
    for tb in rep.get("tables", []):
        t = Table(title=tb["title"], expand=False)
        for h in tb["headers"]:
            t.add_column(str(h), overflow="fold")
        for row in tb["rows"][:50]:
            t.add_row(*[str(row.get(col, "")) for col in tb["columns"]])
        if not tb["rows"]:
            c.print(f"[bold]{tb['title']}:[/] [dim]{tb['empty_message']}[/]")
        else:
            c.print(t)
    for n in rep.get("notes", []):
        c.print(f"[dim]• {n}[/]")
    if rep.get("files"):
        c.print("[bold]Files written:[/] " + ", ".join(rep["files"]))
