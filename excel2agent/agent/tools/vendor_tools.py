"""WF003 Vendor File Processing - column detection and normalisation."""
from __future__ import annotations

import re

from ..models import StepOutcome, ToolError
from . import ToolContext, register_tool
from .data_tools import _auto


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


@register_tool("detect_columns", "Excel/CSV parser", "Map raw headers to canonical fields using alias lists")
def detect_columns(ctx: ToolContext, rows: list, aliases: dict, required: list) -> StepOutcome:
    headers = list(rows[0].keys())
    mapping, used = {}, set()
    for canonical, names in aliases.items():
        candidates = [_key(canonical)] + [_key(n) for n in names]
        for h in headers:
            if h not in used and _key(h) in candidates:
                mapping[h] = canonical
                used.add(h)
                break
    unmapped = [h for h in headers if h not in mapping]
    missing = [r for r in required if r not in mapping.values()]
    if missing:
        raise ToolError(f"Could not detect required column(s) {missing} in headers {headers}. "
                        f"Add the header name to the aliases in config/workflow_bindings.yaml.")
    return StepOutcome({"mapping": mapping, "unmapped": unmapped},
                       "Detected: " + ", ".join(f"'{h.strip()}'→{c}" for h, c in mapping.items()),
                       decisions=[f"Unrecognised columns kept as-is: {unmapped}"] if unmapped else [])


@register_tool("normalize_columns", "Excel/CSV parser", "Rename columns to canonical names and trim values")
def normalize_columns(ctx: ToolContext, rows: list, detection: dict, uppercase: list | None = None) -> StepOutcome:
    mapping = detection["mapping"]
    out = []
    for i, r in enumerate(rows, start=2):           # row 1 is the header in the source file
        new = {"_row": i}
        for h, v in r.items():
            name = mapping.get(h, _key(h).replace(" ", "_"))
            v = v.strip() if isinstance(v, str) else v
            v = _auto(v) if not (name in (uppercase or []) or name == "sku") else v
            if name in (uppercase or []) and isinstance(v, str):
                v = v.upper()
            new[name] = "" if v is None else v
        out.append(new)
    return StepOutcome(out, f"Normalised {len(out)} rows to columns: {', '.join(k for k in out[0] if k != '_row')}",
                       decisions=["Whitespace trimmed; SKUs upper-cased"])
