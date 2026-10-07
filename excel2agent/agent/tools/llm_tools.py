"""LLM tools: structured generation and classification with validation + fallbacks.

Workflows describe *what* to generate in YAML (instructions, inputs, output
fields with length limits). These tools handle the *how*: prompting, JSON
parsing, text validation, one corrective retry, and - when no LLM is configured
or the call fails - a deterministic fallback registered by name.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

from ..llm import LLMError
from ..models import StepOutcome, ToolError
from . import ToolContext, register_tool

_FALLBACKS: dict[str, Callable] = {}

GROUNDING_RULES = """Strict rules:
- Use ONLY facts present in the provided input. Never invent attributes, materials, colours, prices, dates,
  audiences, discounts or claims.
- If a fact needed for the text is missing, write the marker [MISSING: <field>] instead of guessing.
- Respect every max_chars limit."""


def register_fallback(name: str):
    def deco(fn: Callable) -> Callable:
        _FALLBACKS[name] = fn
        return fn
    return deco


def _fallback(name: Optional[str], ctx: ToolContext, **kwargs) -> Any:
    if not name or name not in _FALLBACKS:
        raise ToolError("LLM unavailable and no fallback configured for this step")
    return _FALLBACKS[name](ctx, **kwargs)


def _trim(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:-")
    return cut + "…"


def validate_fields(result: dict, fields: dict) -> list[str]:
    problems = []
    for name, rule in fields.items():
        val = result.get(name)
        if val in (None, "", []):
            problems.append(f"'{name}' is missing")
            continue
        mx = (rule or {}).get("max_chars")
        if mx and isinstance(val, str) and len(val) > mx:
            problems.append(f"'{name}' is {len(val)} chars (max {mx})")
        mn = (rule or {}).get("min_chars")
        if mn and isinstance(val, str) and len(val) < mn:
            problems.append(f"'{name}' is only {len(val)} chars (min {mn})")
    return problems


@register_tool("llm_generate", "LLM", "Generate structured text fields with validation and a fallback")
def llm_generate(ctx: ToolContext, task: str, inputs: dict, fields: dict,
                 instructions: str = "", fallback: Optional[str] = None) -> StepOutcome:
    decisions: list[str] = []
    result: Optional[dict] = None
    if ctx.llm is not None and ctx.llm.available:
        spec = {k: (v or {}).get("description", "") + (f" (max {v['max_chars']} chars)" if (v or {}).get("max_chars") else "")
                for k, v in fields.items()}
        system = f"You are a precise e-commerce/business writer. Task: {task}.\n{instructions}\n{GROUNDING_RULES}"
        user = (f"INPUT DATA:\n{json.dumps(inputs, default=str, indent=1)}\n\n"
                f"Return JSON with exactly these keys: {json.dumps(spec)}")
        try:
            result = ctx.llm.json(system, user)
            problems = validate_fields(result, fields)
            if problems:
                decisions.append("Text validation failed (" + "; ".join(problems) + ") -> asked model to fix")
                result = ctx.llm.json(system, user + "\n\nYour previous answer had problems: "
                                      + "; ".join(problems) + f"\nPrevious answer: {json.dumps(result)}\nFix them.")
            decisions.append(f"Generated with {ctx.llm.mode}")
        except LLMError as exc:
            decisions.append(f"LLM call failed ({exc}) -> deterministic fallback used")
            result = None
    if result is not None:
        still_missing = [k for k in fields if result.get(k) in (None, "", [])]
        if still_missing:
            fb = _fallback(fallback, ctx, inputs=inputs, fields=fields) if fallback in _FALLBACKS else {}
            for k in still_missing:
                if fb.get(k) not in (None, "", []):
                    result[k] = fb[k]
            decisions.append(f"LLM output still missing {still_missing} -> filled from deterministic fallback")
    if result is None:
        result = _fallback(fallback, ctx, inputs=inputs, fields=fields)
        if not any("fallback" in d for d in decisions):
            decisions.append("No LLM configured -> deterministic template fallback used")

    # final text validation (hard limits are always enforced)
    for name, rule in fields.items():
        mx = (rule or {}).get("max_chars")
        if mx and isinstance(result.get(name), str) and len(result[name]) > mx:
            result[name] = _trim(result[name], mx)
            decisions.append(f"'{name}' trimmed to {mx} characters")
    remaining = validate_fields(result, fields)
    if remaining:
        decisions.append("Validation warnings: " + "; ".join(remaining))
    markers = [k for k, v in result.items() if isinstance(v, str) and "[MISSING" in v]
    if markers:
        decisions.append("Missing information explicitly marked in: " + ", ".join(markers))
    summary = "; ".join(f"{k} ({len(v)} chars)" if isinstance(v, str) else k for k, v in result.items())
    return StepOutcome(result, f"Generated {summary}", decisions=decisions)


@register_tool("llm_classify", "LLM/classifier", "Classify rows into fixed labels (batched) with a rule fallback")
def llm_classify(ctx: ToolContext, rows: list, text_field: str, label_field: str, labels: list,
                 instructions: str = "", context: Any = None, fallback: Optional[str] = None,
                 batch_size: int = 40) -> StepOutcome:
    out = [dict(r) for r in rows]
    decisions: list[str] = []
    used_llm = False
    if ctx.llm is not None and ctx.llm.available:
        try:
            for start in range(0, len(out), batch_size):
                batch = out[start:start + batch_size]
                items = {str(i): r[text_field] for i, r in enumerate(batch)}
                system = (f"Classify each item into exactly one of {labels}. {instructions}\n"
                          "Return JSON: {\"labels\": {\"<id>\": \"<label>\"}, \"reasons\": {\"<id>\": \"<short reason>\"}}")
                user = json.dumps({"context": context, "items": items}, default=str)
                res = ctx.llm.json(system, user)
                for i, r in enumerate(batch):
                    lab = str((res.get("labels") or {}).get(str(i), "")).strip().lower()
                    if lab not in labels:
                        raise LLMError(f"invalid label '{lab}' for '{r[text_field]}'")
                    r[label_field] = lab
                    r[f"{label_field}_reason"] = (res.get("reasons") or {}).get(str(i), "")
            used_llm = True
            decisions.append(f"Classified {len(out)} items with {ctx.llm.mode}")
        except LLMError as exc:
            decisions.append(f"LLM classification failed ({exc}) -> rule-based classifier used")
    if not used_llm:
        if not fallback or fallback not in _FALLBACKS:
            raise ToolError("No LLM and no fallback classifier configured")
        for r in out:
            r[label_field], r[f"{label_field}_reason"] = _FALLBACKS[fallback](ctx, text=r[text_field], labels=labels)
        if not decisions:
            decisions.append("No LLM configured -> rule-based classifier used")
    counts: dict = {}
    for r in out:
        counts[r[label_field]] = counts.get(r[label_field], 0) + 1
    return StepOutcome(out, "Labels: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
                       decisions=decisions)
