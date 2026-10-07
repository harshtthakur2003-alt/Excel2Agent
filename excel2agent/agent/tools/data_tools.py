"""Generic, reusable data tools (CSV/Excel reader, calculator, filters, joins, reports).

These are workflow-agnostic. Most workflows are composed mainly from them.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import openpyxl

from ..expressions import evaluate, _num
from ..models import Halt, StepOutcome, ToolError
from . import ToolContext, register_tool

_NUM_RE = re.compile(r"^-?(0|[1-9]\d*)(\.\d+)?$")


def _auto(v: Any) -> Any:
    if isinstance(v, str):
        s = v.strip()
        if _NUM_RE.match(s):
            return float(s) if "." in s else int(s)
        return s
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()[:10]
    return v


def read_rows(path: Path, sheet: Optional[str] = None, raw: bool = False) -> list[dict]:
    if not path.exists():
        raise ToolError(f"File not found: {path.name}")
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            with open(path, newline="", encoding="utf-8-sig") as fh:
                rows = list(csv.DictReader(fh))
        elif suffix in (".xlsx", ".xlsm"):
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb[sheet] if sheet else wb.worksheets[0]
            it = ws.iter_rows(values_only=True)
            header = [str(h) if h is not None else f"column_{i}" for i, h in enumerate(next(it, []))]
            rows = [dict(zip(header, r)) for r in it if any(c not in (None, "") for c in r)]
        elif suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            rows = data if isinstance(data, list) else data.get("rows", [])
        else:
            raise ToolError(f"Unsupported file type '{suffix}' (use .csv, .xlsx or .json)")
    except ToolError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ToolError(f"Could not read {path.name}: {exc}") from exc
    if raw:
        return rows
    return [{k: _auto(v) for k, v in r.items()} for r in rows]


# --------------------------------------------------------------------------- #
@register_tool("load_table", "CSV/Excel reader", "Load rows from a CSV, XLSX or JSON file")
def load_table(ctx: ToolContext, path: str, sheet: Optional[str] = None, raw: bool = False,
               required_columns: Optional[list] = None, ask_if_missing: Optional[str] = None,
               missing_message: Optional[str] = None) -> StepOutcome:
    if not path:
        if ask_if_missing:
            return StepOutcome(None, ask_if_missing, halt=Halt("needs_input", ask_if_missing, ["file"]),
                               decisions=["No file provided -> asking user"])
        raise ToolError("No file path provided")
    p = ctx.path(path)
    if missing_message and not p.exists():
        raise ToolError(missing_message)
    rows = read_rows(p, sheet, raw)
    if not rows:
        raise ToolError(f"{p.name} contains no data rows")
    if required_columns:
        missing = [c for c in required_columns if c not in rows[0]]
        if missing:
            raise ToolError(f"{p.name} is missing required columns: {missing}")
    return StepOutcome(rows, f"Loaded {len(rows)} rows from {p.name} (columns: {', '.join(list(rows[0])[:8])})")


@register_tool("load_tables", "CSV/Excel reader", "Load several files at once into a dict of tables")
def load_tables(ctx: ToolContext, sources: dict) -> StepOutcome:
    out = {name: read_rows(ctx.path(path)) for name, path in sources.items()}
    return StepOutcome(out, "; ".join(f"{k}: {len(v)} rows" for k, v in out.items()))


@register_tool("compute_columns", "calculator", "Add/overwrite columns using safe expressions")
def compute_columns(ctx: ToolContext, rows: list, columns: dict, variables: Optional[dict] = None,
                    explain: Optional[str] = None) -> StepOutcome:
    if rows is None:
        raise ToolError("No rows to compute on")
    variables = variables or {}
    out = []
    for r in rows:
        new = dict(r)
        for col, expr in columns.items():
            new[col] = evaluate(expr, {**new, **variables})
        out.append(new)
    decisions = [explain] if explain else [f"{c} = {e}" for c, e in columns.items()]
    return StepOutcome(out, f"Computed {', '.join(columns)} for {len(out)} rows", decisions=decisions)


@register_tool("filter_rows", "decision rule", "Keep rows matching a condition (a decision rule)")
def filter_rows(ctx: ToolContext, rows: list, condition: str, variables: Optional[dict] = None,
                label: str = "rows") -> StepOutcome:
    variables = variables or {}
    kept = [r for r in rows or [] if evaluate(condition, {**r, **variables})]
    return StepOutcome(kept, f"{len(kept)} of {len(rows or [])} {label} matched: {condition}",
                       decisions=[f"Rule `{condition}` -> {len(kept)} {label} selected"])


@register_tool("partition_rows", "decision rule", "Split rows into matched / unmatched by a condition")
def partition_rows(ctx: ToolContext, rows: list, condition: str, variables: Optional[dict] = None,
                   matched_label: str = "matched", unmatched_label: str = "unmatched") -> StepOutcome:
    variables = variables or {}
    yes, no = [], []
    for r in rows or []:
        (yes if evaluate(condition, {**r, **variables}) else no).append(r)
    return StepOutcome({matched_label: yes, unmatched_label: no},
                       f"{len(yes)} {matched_label}, {len(no)} {unmatched_label}",
                       decisions=[f"Rule `{condition}` -> {len(yes)} {matched_label}"])


@register_tool("join_tables", "data matching", "Match two tables on a (normalised) key")
def join_tables(ctx: ToolContext, left: list, right: list, left_key: str, right_key: str,
                right_prefix: str = "", normalize_keys: bool = True) -> StepOutcome:
    norm = (lambda v: re.sub(r"\s+", "", str(v or "")).upper()) if normalize_keys else (lambda v: v)
    index: dict = {}
    for r in right:
        index.setdefault(norm(r.get(right_key)), r)
    matched, left_only, seen = [], [], set()
    for l in left:
        k = norm(l.get(left_key))
        if k and k in index:
            rr = index[k]
            matched.append({**l, **{f"{right_prefix}{c}": v for c, v in rr.items() if c != right_key}})
            seen.add(k)
        else:
            left_only.append(l)
    right_only = [r for k, r in index.items() if k not in seen]
    return StepOutcome({"matched": matched, "left_only": left_only, "right_only": right_only},
                       f"{len(matched)} matched on {left_key}; {len(left_only)} only internal; {len(right_only)} only vendor",
                       decisions=[f"Keys normalised (trim/upper-case) before matching" if normalize_keys else "Exact key match"])


@register_tool("dedupe_rows", "data cleaning", "Remove duplicate rows by a normalised key expression")
def dedupe_rows(ctx: ToolContext, rows: list, key: str, keep: str = "first",
                merge_sum: Optional[list] = None) -> StepOutcome:
    seen: dict = {}
    removed = []
    for r in rows:
        k = evaluate(key, r)
        if k in seen:
            removed.append(r)
            for f in merge_sum or []:
                seen[k][f] = (_num(seen[k].get(f)) or 0) + (_num(r.get(f)) or 0)
        else:
            seen[k] = dict(r)
    out = list(seen.values())
    return StepOutcome(out, f"{len(rows)} rows -> {len(out)} unique ({len(removed)} duplicates removed)",
                       decisions=[f"Duplicate key: {key}"] + [f"Removed duplicate: {d}" for d in
                                                              [list(r.values())[0] for r in removed][:10]])


@register_tool("annotate_errors", "data validation", "Attach a list of validation errors (_errors) to each row")
def annotate_errors(ctx: ToolContext, rows: list, rules: list) -> StepOutcome:
    out = []
    counts: dict = {}
    for i, r in enumerate(rows, 1):
        errs = []
        for rule in rules:
            ok = evaluate(rule["valid_if"], r)
            if not ok:
                errs.append(rule["message"])
                counts[rule["message"]] = counts.get(rule["message"], 0) + 1
        new = {"_row": r.get("_row", i), **r, "_errors": errs}
        out.append(new)
    return StepOutcome(out, f"Validated {len(out)} rows against {len(rules)} rule(s)",
                       decisions=[f"{m}: {c} row(s)" for m, c in counts.items()] or ["All rows passed"])


@register_tool("validate_params", "input validation", "Check required inputs; ask the user when missing")
def validate_params(ctx: ToolContext, required: Optional[list] = None, require_any: Optional[list] = None,
                    soft: Optional[list] = None, date_fields: Optional[list] = None,
                    date_order: Optional[list] = None, labels: Optional[dict] = None,
                    question: str = "") -> StepOutcome:
    p = ctx.params
    labels = labels or {}
    lab = lambda k: labels.get(k, k.replace("_", " "))  # noqa: E731
    blank = lambda v: v is None or (isinstance(v, (str, list, dict)) and len(v) == 0)  # noqa: E731
    missing = [k for k in required or [] if blank(p.get(k))]
    for group in require_any or []:
        if all(blank(p.get(k)) for k in group):
            missing.append(" or ".join(group))
    errors = []
    parsed = {}
    for f in date_fields or []:
        if not blank(p.get(f)):
            d = parse_date(p[f])
            if d is None:
                errors.append(f"{lab(f).capitalize()} '{p[f]}' is not a valid date (use YYYY-MM-DD).")
            else:
                parsed[f] = d
                p[f] = d.isoformat()
    if date_order and all(k in parsed for k in date_order) and parsed[date_order[0]] > parsed[date_order[1]]:
        errors.append(f"{lab(date_order[0]).capitalize()} ({p[date_order[0]]}) must be before "
                      f"{lab(date_order[1])} ({p[date_order[1]]}).")
    soft_missing = [k for k in soft or [] if blank(p.get(k))]
    present = {k: v for k, v in p.items() if not blank(v)}
    if missing or errors:
        parts = []
        if missing:
            parts.append("Missing required input: " + ", ".join(lab(m) for m in missing) + ".")
        parts.extend(errors)
        if question:
            parts.append(question)
        return StepOutcome({"missing": missing}, " ".join(parts),
                           halt=Halt("needs_input", " ".join(parts), missing),
                           decisions=["Required inputs missing or invalid -> asking user before continuing"])
    decisions = [f"All required inputs present: {', '.join(lab(k) for k in (required or [])) or 'n/a'}"]
    if soft_missing:
        decisions.append("Optional inputs missing (will be marked, not invented): " + ", ".join(map(lab, soft_missing)))
    return StepOutcome({"present": present, "missing_soft": soft_missing},
                       f"Inputs valid; {len(soft_missing)} optional field(s) missing", decisions=decisions)


@register_tool("require_rows", "decision rule", "Stop and ask the user if a lookup returned nothing")
def require_rows(ctx: ToolContext, rows: Any, message: str, status: str = "needs_input") -> StepOutcome:
    if not rows:
        return StepOutcome(rows, message, halt=Halt(status, message), decisions=["Nothing found -> " + status])
    return StepOutcome(rows, f"{len(rows)} record(s) found")


@register_tool("aggregate", "calculator", "Group rows and compute count/sum/avg/min/max/rate metrics")
def aggregate(ctx: ToolContext, rows: list, group_by: list, metrics: dict) -> StepOutcome:
    groups: dict = {}
    for r in rows:
        groups.setdefault(tuple(r.get(g) for g in group_by), []).append(r)
    out = []
    for key, items in groups.items():
        row = dict(zip(group_by, key))
        for name, m in metrics.items():
            op = m["op"]
            vals = [_num(i.get(m.get("field"))) for i in items if m.get("field")]
            vals = [v for v in vals if isinstance(v, (int, float))]
            if op == "count":
                row[name] = len(items)
            elif op == "count_if":
                row[name] = sum(1 for i in items if evaluate(m["condition"], i))
            elif op == "rate_if":
                row[name] = round(100 * sum(1 for i in items if evaluate(m["condition"], i)) / len(items), 1)
            elif op == "sum":
                row[name] = round(sum(vals), 2)
            elif op == "avg":
                row[name] = round(sum(vals) / len(vals), 1) if vals else None
            elif op == "max":
                row[name] = max(vals) if vals else None
            elif op == "min":
                row[name] = min(vals) if vals else None
        out.append(row)
    return StepOutcome(out, f"Aggregated {len(rows)} rows into {len(out)} groups by {', '.join(group_by)}")


@register_tool("build_report", "reporting", "Assemble the final structured report (tables, metrics, sections, exports)")
def build_report(ctx: ToolContext, title: str, summary: str = "", vars: Optional[dict] = None,
                 computed: Optional[dict] = None, metrics: Optional[dict] = None,
                 tables: Optional[list] = None, sections: Optional[list] = None,
                 exports: Optional[list] = None, notes: Optional[list] = None,
                 extra_files: Optional[list] = None) -> StepOutcome:
    env = dict(vars or {})
    for k, expr in (computed or {}).items():
        env[k] = evaluate(expr, env)
    report: dict = {"title": title, "summary": "", "metrics": {}, "tables": [], "sections": [],
                    "files": [], "notes": [n for n in (notes or []) if n]}
    for label, expr in (metrics or {}).items():
        report["metrics"][label] = env[expr] if expr in env else evaluate(str(expr), env)
    for t in tables or []:
        rows = t.get("rows") or []
        if t.get("when") and not evaluate(t["when"], env):
            continue
        if t.get("where"):
            rows = [r for r in rows if evaluate(t["where"], {**r, **env})]
        if t.get("sort_by"):
            rows = sorted(rows, key=lambda r: (_num(r.get(t["sort_by"])) is None, _num(r.get(t["sort_by"])) or 0),
                          reverse=bool(t.get("descending")))
            if t.get("descending"):  # keep None last
                rows = [r for r in rows if r.get(t["sort_by"]) is not None] + [r for r in rows if r.get(t["sort_by"]) is None]
        if t.get("limit"):
            rows = rows[: int(t["limit"])]
        cols = t.get("columns") or (list(rows[0].keys()) if rows else [])
        if not rows and t.get("hide_if_empty"):
            continue
        report["tables"].append({"title": t.get("title", ""), "columns": cols,
                                 "headers": t.get("headers") or cols,
                                 "rows": [{c: _fmt(r.get(c)) for c in cols} for r in rows],
                                 "empty_message": t.get("empty_message", "None")})
    for s in sections or []:
        if s.get("when") and not evaluate(s["when"], env):
            continue
        if s.get("content") not in (None, "", [], {}):
            report["sections"].append({"title": s.get("title", ""), "content": s["content"]})
    report["files"].extend(f for f in extra_files or [] if f)
    for e in exports or []:
        path = ctx.path(e["path"])
        if e.get("prefix_from"):
            path = path.with_name(f"{Path(e['prefix_from']).stem}_{path.name}")
        path = write_csv(path, e.get("rows") or [], e.get("columns"))
        report["files"].append(str(path.relative_to(ctx.base_dir)) if path.is_relative_to(ctx.base_dir) else str(path))
    try:
        report["summary"] = summary.format(**env)
    except (KeyError, IndexError, ValueError):
        report["summary"] = summary
    return StepOutcome(report, report["summary"])


# --------------------------------------------------------------------------- #
def _fmt(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, list):
        return "; ".join(map(str, v))
    return v


def write_csv(path: Path, rows: list, columns: Optional[list] = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = columns or (list(rows[0].keys()) if rows else [])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: _fmt(r.get(c)) for c in cols})
    return path


def parse_date(v: Any) -> Optional[date]:
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d %B %Y", "%d %b %Y", "%B %d %Y",
                "%B %d, %Y", "%b %d, %Y", "%b %d %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
