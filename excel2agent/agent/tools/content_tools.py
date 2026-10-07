"""WF004 Product Description Generator and WF007 Marketing Campaign Brief.

LLM generation itself is done by the generic ``llm_generate`` tool; this module
supplies (a) deterministic, *grounded* fallbacks used when no LLM is configured
and (b) the non-LLM campaign tools (product summary, timeline/checklist).
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Optional

from ..models import Halt, StepOutcome
from . import ToolContext, register_tool
from .data_tools import parse_date, read_rows
from .llm_tools import register_fallback


def _m(v: Any, field: str) -> str:
    if v in (None, "", [], {}):
        return f"[MISSING: {field}]"
    if isinstance(v, list):
        return ", ".join(map(str, v))
    if isinstance(v, dict):
        return ", ".join(f"{k}: {x}" for k, x in v.items())
    return str(v)


# --------------------------------------------------------------------------- #
# WF004 fallbacks (grounded templates: only provided facts, missing ones marked)
# --------------------------------------------------------------------------- #
def _product(inputs: dict) -> dict:
    return inputs.get("product", inputs)


@register_fallback("product_description")
def fb_description(ctx, inputs, fields):
    p = _product(inputs)
    attrs = p.get("attributes")
    attr_txt = (f"Key features: {_m(attrs, 'attributes')}." if attrs else "Key features: [MISSING: attributes].")
    cat = str(p['category']).lower()
    article = "an" if cat[:1] in "aeiou" else "a"
    text = (f"The {p['product_name']} is {article} {cat} piece in {_m(p.get('color'), 'color')}, "
            f"made from {_m(p.get('material'), 'material')}. {attr_txt} "
            f"Designed for {_m(p.get('target_audience'), 'target_audience')}.")
    return {"description": text}


@register_fallback("product_short_description")
def fb_short(ctx, inputs, fields):
    p = _product(inputs)
    first_attr = ""
    attrs = p.get("attributes")
    if isinstance(attrs, list) and attrs:
        first_attr = f", featuring {' and '.join(map(str, attrs[:2]))}"
    elif isinstance(attrs, str) and attrs:
        first_attr = f", featuring {attrs.split(',')[0].strip()}"
    color = _m(p.get('color'), 'color')
    color = color if color.startswith("[MISSING") else color[:1].upper() + color[1:]
    return {"short_description": f"{color} {p['product_name']} in "
                                 f"{_m(p.get('material'), 'material')}{first_attr}."}


@register_fallback("product_seo_title")
def fb_seo_title(ctx, inputs, fields):
    p = _product(inputs)
    parts = [p["product_name"]]
    if p.get("color"):
        parts.append(str(p["color"]).title())
    title = " - ".join(parts) + f" | {p['category']}"
    return {"seo_title": title}


@register_fallback("product_meta_description")
def fb_meta(ctx, inputs, fields):
    p = _product(inputs)
    return {"meta_description": f"Shop the {p['product_name']}: {_m(p.get('material'), 'material')} "
                                f"{str(p['category']).lower()} in {_m(p.get('color'), 'color')}. "
                                f"Made for {_m(p.get('target_audience'), 'target_audience')}."}


# --------------------------------------------------------------------------- #
# WF007 campaign brief
# --------------------------------------------------------------------------- #
OBJECTIVES = [
    ("conversion", ["sales", "revenue", "sell", "conversion", "orders", "purchase", "clear stock"]),
    ("acquisition", ["new customers", "acquire", "sign up", "signups", "subscribers", "leads"]),
    ("retention", ["loyal", "repeat", "retention", "existing customers", "win back"]),
    ("awareness", ["launch", "awareness", "introduce", "announce", "visibility", "buzz"]),
]
KPI = {"conversion": "Revenue & conversion rate", "acquisition": "New customers / sign-ups",
       "retention": "Repeat purchase rate", "awareness": "Reach, impressions & site visits"}


@register_fallback("campaign_objective")
def fb_objective(ctx, inputs, fields):
    goal = str(inputs.get("campaign_goal", "")).lower()
    otype = next((o for o, words in OBJECTIVES if any(w in goal for w in words)), "awareness")
    return {"objective_type": otype, "objective": inputs.get("campaign_goal"), "primary_kpi": KPI[otype]}


@register_fallback("campaign_messaging")
def fb_messaging(ctx, inputs, fields):
    prods = inputs.get("products") or []
    names = ", ".join(p["product_name"] for p in prods[:3]) or "[MISSING: products]"
    mats = sorted({p.get("material") for p in prods if p.get("material")})
    promo = inputs.get("promotion")
    audience = _m(inputs.get("target_audience"), "target_audience")
    key = f"{inputs.get('collection') or 'The collection'} is here: {names}" + (f" - {promo}." if promo else ".")
    return {"key_message": key,
            "tagline": f"{inputs.get('collection') or 'New season'}, made to last.",
            "supporting_points": [f"Materials: {', '.join(mats)}" if mats else "Materials: [MISSING: materials]",
                                  f"Audience: {audience}",
                                  f"Offer: {promo}" if promo else "Offer: [MISSING: promotion]"]}


@register_fallback("campaign_channels")
def fb_channels(ctx, inputs, fields):
    otype = (inputs.get("objective") or {}).get("objective_type", "awareness")
    base = {
        "awareness": ["Instagram & Reels (visual launch content)", "Influencer seeding", "Email announcement to full list"],
        "conversion": ["Email + SMS with promotion", "Paid social retargeting", "Google Shopping / Performance Max"],
        "acquisition": ["Paid social prospecting (lookalikes)", "Referral offer", "SEO landing page"],
        "retention": ["Loyalty email series", "Personalised recommendations", "Early-access for members"],
    }[otype]
    return {"channel_recommendations": base + ["Homepage hero banner"]}


@register_tool("select_campaign_products", "product data reader", "Pick and summarise the products in the campaign")
def select_campaign_products(ctx: ToolContext, path: str, product_list: Optional[list] = None,
                             collection: Optional[str] = None, request: str = "",
                             new_collection: Optional[str] = None) -> StepOutcome:
    rows = read_rows(ctx.path(path))
    decisions = []
    if product_list:
        wanted = [str(x).lower().strip() for x in product_list]
        chosen = [r for r in rows if any(w in (str(r["sku"]).lower(), r["product_name"].lower())
                                         or w in r["product_name"].lower() for w in wanted)]
        decisions.append(f"Products taken from the request: {product_list}")
    else:
        if not collection and new_collection and re.search(r"\bnew (collection|season|arrivals)\b", request or "", re.I):
            collection = new_collection
            decisions.append(f"'new collection' resolved to the latest collection in product data: {new_collection}")
        if collection:
            names = sorted({str(r.get("collection", "")) for r in rows}, reverse=True)
            if collection.lower() not in [n.lower() for n in names]:
                partial = [n for n in names if n.lower().startswith(collection.lower())]
                if partial:
                    resolved = new_collection if new_collection in partial else partial[0]
                    decisions.append(f"Collection '{collection}' resolved to '{resolved}'")
                    collection = resolved
        chosen = [r for r in rows if collection and str(r.get("collection", "")).lower() == collection.lower()]
        decisions.append(f"Products filtered by collection = {collection}")
    if not chosen:
        msg = (f"I couldn't find products for this campaign{f' (collection: {collection})' if collection else ''}. "
               "Which products or collection should it feature? (e.g. 'products: SKU-1001, SKU-1004' or 'Autumn 2026 collection')")
        return StepOutcome(None, msg, halt=Halt("needs_input", msg, ["product_list"]),
                           decisions=decisions + ["No products resolved -> asking user"])
    prices = [float(r["price"]) for r in chosen if r.get("price") not in (None, "")]
    summary = {"collection": collection, "count": len(chosen),
               "categories": sorted({r["category"] for r in chosen}),
               "price_range": f"${min(prices):.0f}-${max(prices):.0f}" if prices else "n/a",
               "products": [{k: r.get(k) for k in ("sku", "product_name", "category", "price", "material", "color")}
                            for r in chosen]}
    return StepOutcome(summary, f"{len(chosen)} products ({', '.join(summary['categories'])}), {summary['price_range']}",
                       decisions=decisions)


@register_tool("build_campaign_plan", "planning", "Build timeline milestones and the campaign checklist")
def build_campaign_plan(ctx: ToolContext, start_date: str, end_date: str, channels: list,
                        promotion: Optional[str] = None, today: Optional[str] = None) -> StepOutcome:
    s, e = parse_date(start_date), parse_date(end_date)
    t = parse_date(today) if today else date.today()
    lead = (s - t).days
    decisions = []
    if lead < 0:
        decisions.append(f"Start date is {-lead} day(s) in the past -> timeline shown for reference; confirm the dates")
    elif lead < 14:
        decisions.append(f"Only {lead} day(s) until launch (< 14) -> compressed prep timeline, flagged as risk")
    prep = max(lead, 1)
    timeline = [
        {"milestone": "Brief approved & assets requested", "date": (s - timedelta(days=min(14, prep))).isoformat()},
        {"milestone": "Creative & copy final", "date": (s - timedelta(days=min(7, prep))).isoformat()},
        {"milestone": "Channels scheduled, tracking (UTMs) tested", "date": (s - timedelta(days=min(2, prep))).isoformat()},
        {"milestone": "Campaign launch", "date": s.isoformat()},
        {"milestone": "Mid-campaign performance check", "date": (s + (e - s) / 2).isoformat()},
        {"milestone": "Campaign end", "date": e.isoformat()},
        {"milestone": "Post-campaign report", "date": (e + timedelta(days=3)).isoformat()},
    ]
    checklist = ["Confirm campaign goal, KPI and budget with stakeholders",
                 "Verify product stock levels for featured products (see Inventory Restock workflow)",
                 "Validate product prices before launch (see Price Validation workflow)",
                 "Produce creative for: " + ", ".join(c.split(" (")[0] for c in channels[:4]),
                 "Legal/brand review of copy and claims",
                 "Set up UTM tracking and analytics dashboard",
                 "Schedule posts / emails / ads per timeline"]
    checklist.insert(3, f"Configure promotion in checkout: {promotion}" if promotion
                     else "Decide promotion (currently [MISSING: promotion])")
    return StepOutcome({"timeline": timeline, "checklist": checklist, "duration_days": (e - s).days + 1,
                        "lead_days": lead},
                       f"{len(timeline)} milestones, {len(checklist)} checklist items, {(e - s).days + 1}-day campaign",
                       decisions=decisions)
