"""WF008 SEO Keyword Classification - rule-based intent fallback and category mapping."""
from __future__ import annotations

import re
from pathlib import Path

from ..models import StepOutcome
from . import ToolContext, register_tool
from .data_tools import read_rows, write_csv
from .llm_tools import register_fallback

INTENT_RULES = [
    ("navigational", ["northline", "login", "log in", "tracking", "track order", "returns policy", "contact", "account", "store locator"]),
    ("transactional", ["buy", "order", "price", "sale", "discount", "coupon", "code", "cheap", "deal", "shop", "online", "near me"]),
    ("commercial", ["best", "top", "review", "reviews", "vs", "versus", "compare", "rated", "alternative"]),
    ("informational", ["how", "what", "why", "guide", "ways", "tips", "wash", "care", "style", "tie", "is"]),
]


@register_fallback("keyword_intent_rules")
def keyword_intent_rules(ctx: ToolContext, text: str, labels: list) -> tuple[str, str]:
    low = f" {text.lower()} "
    for label, words in INTENT_RULES:
        hits = [w for w in words if re.search(rf"\b{re.escape(w)}\b", low)]
        if hits:
            return label, f"rule: contains '{hits[0]}'"
    return "commercial", "rule: bare product term (shopping research)"


@register_tool("map_keyword_categories", "classifier", "Map keywords to product categories and target pages")
def map_keyword_categories(ctx: ToolContext, rows: list, categories_path: str, nav_pages: dict,
                           fallback_page: str = "/") -> StepOutcome:
    categories = read_rows(ctx.path(categories_path))
    out, unmapped = [], 0
    for r in rows:
        kw = r["keyword"].lower()
        best, best_hits = None, 0
        for c in categories:
            hits = sum(1 for t in str(c["terms"]).split(";") if re.search(rf"\b{re.escape(t.strip())}", kw))
            if hits > best_hits:
                best, best_hits = c, hits
        new = dict(r)
        new["category"] = best["category"] if best else "General / Brand"
        if r["intent"] == "navigational":
            page = next((p for k, p in nav_pages.items() if k in kw), fallback_page)
        elif best is None:
            page = fallback_page
        elif r["intent"] == "informational":
            page = best["guide_page"]
        else:
            page = best["page"]
        new["target_page"] = page
        if not best:
            unmapped += 1
        out.append(new)
    return StepOutcome(out, f"Mapped {len(out) - unmapped} keywords to product categories; {unmapped} brand/general",
                       decisions=["Transactional/commercial → category page; informational → guide/blog page; "
                                  "navigational → brand utility page"])


@register_tool("export_table", "reporting", "Export rows to a CSV file under outputs/")
def export_table(ctx: ToolContext, rows: list, path: str, columns: list | None = None,
                 prefix_from: str | None = None) -> StepOutcome:
    p = ctx.path(path)
    if prefix_from:                      # e.g. vendor_acme_products.xlsx -> vendor_acme_products_cleaned.csv
        p = p.with_name(f"{Path(prefix_from).stem}_{p.name}")
    p = write_csv(p, rows, columns)
    return StepOutcome(str(p.relative_to(ctx.base_dir)), f"Exported {len(rows)} rows to {p.relative_to(ctx.base_dir)}")
