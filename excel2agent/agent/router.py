"""Workflow selection ("Identify Workflow" in the architecture).

Two interchangeable strategies, both driven entirely by the registry - there is
no per-workflow routing code:

1. **LLM tool calling** (OpenAI). Every workflow in the Excel file is exposed to
   the model as one function whose description is built from the Excel columns
   and whose JSON-schema parameters come from the YAML binding. The model picks
   the function (= workflow) *and* extracts its parameters in a single call. A
   ``no_matching_workflow`` function lets it refuse out-of-scope requests.
2. **Offline lexical router** (fallback, no API key). TF-IDF cosine similarity
   between the request and each workflow's Excel text, plus regex/keyword
   parameter extraction declared per parameter in YAML.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Optional

from .llm import LLMClient, LLMError
from .models import ParamSpec, RoutingDecision, WorkflowSpec
from .registry import WorkflowRegistry

NO_MATCH_TOOL = "no_matching_workflow"
MIN_OFFLINE_SCORE = 0.10

SYSTEM_PROMPT = """You are the routing brain of a business workflow agent.
Each available function is one business workflow defined in the company's workflow catalogue.
Choose the single workflow whose trigger and purpose best matches the user's request and fill its parameters.
Rules:
- Only fill a parameter if its value is explicitly stated in the request or the attached data. NEVER invent values
  (no made-up dates, goals, attributes, IDs or emails). Leave unknown parameters out - the workflow will ask for them.
- Always set `confidence` (0-1) and a one-sentence `reasoning` explaining the choice.
- If no workflow fits the request, call `no_matching_workflow`."""

STOPWORDS = set("""a an the and or of to for in on at by with from this that these those is are be it its
me my our we you your i please can could would should will which what where who how show find give get
do does any all some into as about than then them they their there here also just new""".split())


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [_stem(w) for w in words if w not in STOPWORDS and len(w) > 1]


def _stem(w: str) -> str:
    for suf in ("ing", "ies", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


class Router:
    def __init__(self, registry: WorkflowRegistry, llm: LLMClient):
        self.registry = registry
        self.llm = llm
        self._build_index()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def route(self, request: str, attachments: Optional[dict] = None,
              pending: Optional[dict] = None) -> RoutingDecision:
        attachments = attachments or {}
        decision = None
        if self.llm.available:
            try:
                decision = self._route_llm(request, attachments, pending)
            except Exception as exc:  # noqa: BLE001 - any LLM/parsing problem -> offline router
                decision = self._route_offline(request, pending)
                decision.reasoning += f" (LLM routing failed, used offline router: {exc})"
        else:
            decision = self._route_offline(request, pending)

        if decision.workflow_id:
            spec = self.registry.get(decision.workflow_id)
            decision.params = self._finalise_params(spec, request, decision.params, attachments, pending)
        return decision

    def tool_schemas(self) -> list[dict]:
        """OpenAI function definitions generated from the registry (one per workflow)."""
        tools = []
        for spec in self.registry.workflows.values():
            props = {p.name: p.json_schema() for p in spec.params if p.llm}
            props["confidence"] = {"type": "number", "description": "0-1 confidence that this is the right workflow"}
            props["reasoning"] = {"type": "string", "description": "One sentence: why this workflow"}
            desc = (f"{spec.name}. Use when: {spec.trigger}. Inputs: {spec.inputs}. "
                    f"Decision logic: {spec.decision_logic}. Produces: {spec.expected_output}.")
            if spec.description:
                desc += f" {spec.description}"
            tools.append({"type": "function", "function": {
                "name": spec.tool_name, "description": desc[:1000],
                "parameters": {"type": "object", "properties": props,
                               "required": ["confidence", "reasoning"]}}})
        tools.append({"type": "function", "function": {
            "name": NO_MATCH_TOOL,
            "description": "Call when the request does not match any available workflow.",
            "parameters": {"type": "object", "properties": {"reasoning": {"type": "string"}},
                           "required": ["reasoning"]}}})
        return tools

    # ------------------------------------------------------------------ #
    # LLM routing
    # ------------------------------------------------------------------ #
    def _route_llm(self, request: str, attachments: dict, pending: Optional[dict]) -> RoutingDecision:
        user = f"User request: {request}"
        if attachments:
            user += f"\n\nAttached data (JSON): {attachments}"
        if pending:
            spec = self.registry.get(pending["workflow_id"])
            user = (f"Context: the user is answering a follow-up question from workflow '{spec.name}'. "
                    f"They were asked: \"{pending['message']}\". Previously known parameters: {pending['params']}.\n"
                    f"If the message answers that question, choose that workflow again and extract the new values.\n\n"
                    + user)
        name, args = self.llm.tool_call(SYSTEM_PROMPT, user, self.tool_schemas())
        try:
            confidence = max(0.0, min(1.0, float(args.pop("confidence", 0.8) or 0.8)))
        except (TypeError, ValueError):
            confidence = 0.8
        reasoning = str(args.pop("reasoning", ""))
        if name == NO_MATCH_TOOL:
            return RoutingDecision(None, {}, 0.0, reasoning or "No workflow matches", "llm-tool-calling")
        spec = next((s for s in self.registry.workflows.values() if s.tool_name == name), None)
        if spec is None:
            raise LLMError(f"Model called unknown function {name}")
        method = "llm-tool-calling"
        if pending and spec.id == pending["workflow_id"]:
            method += " (follow-up)"
        return RoutingDecision(spec.id, args, confidence, reasoning, method)

    # ------------------------------------------------------------------ #
    # Offline routing
    # ------------------------------------------------------------------ #
    def _build_index(self) -> None:
        docs = {wid: tokenize(s.routing_text()) for wid, s in self.registry.workflows.items()}
        n = len(docs) or 1
        df = Counter(t for toks in docs.values() for t in set(toks))
        self._idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self._vectors = {wid: self._vec(toks) for wid, toks in docs.items()}

    def _vec(self, toks: list[str]) -> dict:
        tf = Counter(toks)
        v = {t: c * self._idf.get(t, 0.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def score(self, request: str) -> list[tuple[str, float]]:
        q = self._vec(tokenize(request))
        scores = [(wid, sum(q.get(t, 0) * w for t, w in vec.items())) for wid, vec in self._vectors.items()]
        return sorted(scores, key=lambda x: -x[1])

    def _route_offline(self, request: str, pending: Optional[dict]) -> RoutingDecision:
        ranked = self.score(request)
        top_id, top = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        cands = [(w, round(s, 3)) for w, s in ranked[:3]]

        if pending:
            p_spec = self.registry.get(pending["workflow_id"])
            answered = extract_params(p_spec, request)
            switching = top_id != p_spec.id and top >= 0.25 and not answered
            if not switching:
                return RoutingDecision(p_spec.id, answered, 0.9,
                                       f"Treated message as an answer to the pending '{p_spec.name}' question.",
                                       "pending-followup", cands)

        if top < MIN_OFFLINE_SCORE:
            return RoutingDecision(None, {}, round(top, 3),
                                   "No workflow matched the request with enough similarity.",
                                   "offline-lexical", cands)
        spec = self.registry.get(top_id)
        confidence = round(0.4 * min(top / 0.5, 1.0) + 0.6 * (top - second) / top, 2)
        overlap = sorted(set(tokenize(request)) & set(self._vectors[top_id]))
        reasoning = f"Best lexical match to '{spec.name}' (score {top:.2f} vs next {second:.2f}); shared terms: {', '.join(overlap[:8])}."
        return RoutingDecision(top_id, extract_params(spec, request), confidence, reasoning, "offline-lexical", cands)

    # ------------------------------------------------------------------ #
    def _finalise_params(self, spec: WorkflowSpec, request: str, params: dict,
                         attachments: dict, pending: Optional[dict]) -> dict:
        """Merge precedence: defaults < previous (follow-up) < regex < LLM < attachments."""
        out: dict = {}
        for p in spec.params:
            if p.default is not None:
                out[p.name] = p.default
        if pending and pending.get("workflow_id") == spec.id:
            # keep earlier answers, except the fields the agent asked to be replaced (e.g. "order_id or email")
            asked = {part.strip().replace(" ", "_") for m in pending.get("missing", [])
                     for part in re.split(r"\s+or\s+|,", m)}
            out.update({k: v for k, v in pending.get("params", {}).items()
                        if v not in (None, "", []) and k not in asked})
        out.update(extract_params(spec, request))
        out.update({k: v for k, v in (params or {}).items() if v not in (None, "", [])})
        known = {p.name for p in spec.params}
        for k, v in attachments.items():
            if k in known:
                out[k] = v
            elif isinstance(v, dict):                    # e.g. {"product": {...}} -> spread known keys
                out.update({kk: vv for kk, vv in v.items() if kk in known})
        return {k: _coerce(next((p for p in spec.params if p.name == k), None), v) for k, v in out.items()}


# --------------------------------------------------------------------------- #
def extract_params(spec: WorkflowSpec, text: str) -> dict:
    """Offline, declarative parameter extraction (regex + keyword maps from YAML)."""
    found: dict = {}
    for p in spec.params:
        if p.pattern:
            m = re.search(p.pattern, text or "", re.I | re.S)
            if m:
                groups = [g for g in m.groups() if g] if m.groups() else []
                found[p.name] = (groups[0] if groups else m.group(0)).strip()
        elif p.keywords:
            low = (text or "").lower()
            for value, words in p.keywords.items():
                if any(re.search(rf"\b{re.escape(w.lower())}\b", low) for w in words):
                    found[p.name] = value
                    break
    return {k: _coerce(next(p for p in spec.params if p.name == k), v) for k, v in found.items()}


def _coerce(p: Optional[ParamSpec], v):
    if p is None or v is None:
        return v
    try:
        if p.type == "integer":
            return int(float(str(v).replace(",", "")))
        if p.type == "number":
            return float(str(v).replace(",", "").rstrip("%"))
        if p.type == "array" and isinstance(v, str):
            return [x.strip() for x in re.split(r",|;|\band\b", v) if x.strip()]
    except ValueError:
        return v
    return v
