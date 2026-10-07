"""WF006 Duplicate Product Detection - identifier comparison, attribute similarity, grouping."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from itertools import combinations

from ..expressions import _num
from ..models import StepOutcome
from . import ToolContext, register_tool

SYNONYMS = {"medium": "m", "large": "l", "small": "s", "gray": "grey", "tshirt": "t shirt", "tee": "t shirt",
            "pullover": "pull over", "eu": ""}


def normalize_name(text: str) -> str:
    t = re.sub(r"[^a-z0-9 ]+", " ", str(text or "").lower())
    t = " ".join(SYNONYMS.get(w, w) for w in t.split())
    return re.sub(r"\s+", " ", t).strip()


def token_sim(a: str, b: str) -> float:
    ta, tb = set(a.split()), set(b.split())
    jac = len(ta & tb) / len(ta | tb) if ta | tb else 0
    seq = SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio()
    return round(max(jac, seq), 3)


@register_tool("normalize_products", "text similarity", "Normalise SKUs, names and attributes for comparison")
def normalize_products(ctx: ToolContext, rows: list, attributes: list) -> StepOutcome:
    out = []
    for i, r in enumerate(rows, 1):
        n = dict(r)
        n["_id"] = i
        n["norm_sku"] = re.sub(r"\s+", "", str(r.get("sku", ""))).upper()
        n["norm_name"] = normalize_name(r.get("product_name"))
        for a in attributes:
            n[f"norm_{a}"] = normalize_name(r.get(a))
        out.append(n)
    return StepOutcome(out, f"Normalised {len(out)} products (SKU upper/trim; names lower-cased, punctuation & synonyms unified)")


@register_tool("compare_identifiers", "text similarity", "Find exact SKU matches (definite duplicates)")
def compare_identifiers(ctx: ToolContext, rows: list) -> StepOutcome:
    by_sku: dict = {}
    for r in rows:
        if r["norm_sku"]:                     # blank SKUs are not evidence of duplication
            by_sku.setdefault(r["norm_sku"], []).append(r)
    pairs = []
    for sku, items in by_sku.items():
        for a, b in combinations(items, 2):
            pairs.append({"a": a["_id"], "b": b["_id"], "score": 1.0, "type": "definite",
                          "matching_fields": ["sku"] + [f for f in ("product_name", "brand", "color", "size", "price")
                                                       if str(a.get(f)).strip().lower() == str(b.get(f)).strip().lower()],
                          "reason": f"Exact SKU match ({sku})"})
    return StepOutcome(pairs, f"{len(pairs)} exact-SKU pair(s) found",
                       decisions=["Rule: exact SKU match (after normalisation) = definite duplicate"])


@register_tool("compare_attributes", "text similarity", "Score attribute similarity for pairs with different SKUs")
def compare_attributes(ctx: ToolContext, rows: list, exclude_pairs: list, weights: dict,
                       min_name_similarity: float, possible_threshold: float, price_tolerance_pct: float,
                       variant_attributes: list | None = None) -> StepOutcome:
    done = {(p["a"], p["b"]) for p in exclude_pairs}
    pairs, rejected, variants = [], 0, []
    for a, b in combinations(rows, 2):
        if (a["_id"], b["_id"]) in done or (a["norm_sku"] and a["norm_sku"] == b["norm_sku"]):
            continue
        name_sim = token_sim(a["norm_name"], b["norm_name"])
        if name_sim < min_name_similarity:
            continue
        diff = [v for v in (variant_attributes or [])
                if a.get(f"norm_{v}") and b.get(f"norm_{v}") and a[f"norm_{v}"] != b[f"norm_{v}"]]
        if diff:                       # same product family but different size/colour = a variant, not a duplicate
            variants.append(f"{str(a['sku']).strip()} vs {str(b['sku']).strip()}: different {', '.join(diff)}")
            continue
        scores, matching = {"name": name_sim}, []
        if name_sim >= 0.85:
            matching.append("product_name~")
        for attr in ("brand", "color", "size"):
            same = a.get(f"norm_{attr}") == b.get(f"norm_{attr}")
            scores[attr] = 1.0 if same else 0.0
            if same:
                matching.append(attr)
        pa, pb = _num(a.get("price")), _num(b.get("price"))
        price_ok = bool(pa and pb and abs(pa - pb) / max(pa, pb) * 100 <= price_tolerance_pct)
        scores["price"] = 1.0 if price_ok else 0.0
        if price_ok:
            matching.append("price≈")
        total = round(sum(scores[k] * w for k, w in weights.items()) / sum(weights.values()), 3)
        if total >= possible_threshold:
            pairs.append({"a": a["_id"], "b": b["_id"], "score": total, "type": "possible",
                          "matching_fields": matching,
                          "reason": f"name similarity {name_sim:.2f}; same {', '.join(m for m in matching if m.isalpha()) or 'nothing else'}"})
        else:
            rejected += 1
    return StepOutcome(pairs, f"{len(pairs)} possible duplicate pair(s); {len(variants)} variant pair(s) and "
                              f"{rejected} low-score pair(s) rejected",
                       decisions=[f"Weighted score = {weights}; possible duplicate if ≥ {possible_threshold}"]
                       + [f"Variant, not duplicate: {v}" for v in variants])


@register_tool("group_duplicates", "grouping", "Union-find pairs into duplicate groups")
def group_duplicates(ctx: ToolContext, rows: list, pairs: list) -> StepOutcome:
    if pairs and isinstance(pairs[0], list):          # accept [[...sku pairs], [...attribute pairs]]
        pairs = [p for group in pairs for p in (group or [])]
    parent = {r["_id"]: r["_id"] for r in rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in pairs:
        parent[find(p["a"])] = find(p["b"])
    groups: dict = {}
    for r in rows:
        groups.setdefault(find(r["_id"]), []).append(r)
    by_id = {r["_id"]: r for r in rows}
    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        ids = {m["_id"] for m in members}
        gp = [p for p in pairs if p["a"] in ids]
        out.append({"members": members, "pairs": gp})
    return StepOutcome(out, f"{len(out)} duplicate group(s) covering {sum(len(g['members']) for g in out)} products")


@register_tool("assign_confidence", "scoring", "Assign Definite/High/Medium confidence per group")
def assign_confidence(ctx: ToolContext, groups: list, high_threshold: float) -> StepOutcome:
    def pair_level(p):
        if p["type"] == "definite":
            return "Definite"
        return "High" if p["score"] >= high_threshold else "Medium"

    order = {"Definite": 0, "High": 1, "Medium": 2}
    out = []
    for g in groups:
        levels = sorted({pair_level(p) for p in g["pairs"]}, key=order.get)
        fields = sorted({f for p in g["pairs"] for f in p["matching_fields"]})
        out.append({"confidence": " + ".join(levels), "score": max(p["score"] for p in g["pairs"]),
                    "skus": ", ".join(str(m["sku"]).strip() for m in g["members"]),
                    "products": " | ".join(m["product_name"] for m in g["members"]),
                    "matching_fields": ", ".join(fields),
                    "reason": "; ".join(sorted({p["reason"] for p in g["pairs"]})),
                    "_rank": order[levels[0]]})
    out.sort(key=lambda r: (r["_rank"], -r["score"]))
    for i, r in enumerate(out, 1):
        r.pop("_rank")
        r["group"] = f"G{i}"
    return StepOutcome(out, ", ".join(f"{r['group']}={r['confidence']}" for r in out),
                       decisions=[f"Definite = exact SKU; High = attribute score ≥ {high_threshold}; Medium = below. "
                                  "Mixed groups show both levels (e.g. 'Definite + High')."])
