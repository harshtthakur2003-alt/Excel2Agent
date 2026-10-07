# Loom walkthrough script (~10–12 min)

A suggested structure that covers every point the evaluators listed. Put your words in your own voice. The
commands are copy-paste ready.

**Before recording:** `pip install -r requirements.txt`, put `OPENAI_API_KEY` in `.env`, run
`python scripts/run_examples.py` once, and open the repo in your editor plus two terminals. Use a wide terminal
window, or the Streamlit UI.

---

### 0. Intro (30 s)
- "This is an Excel-driven agent. One LangGraph agent runs all 10 workflows, so there are no separate chatbots."
- Show the README diagram: *User request → Agent → Identify workflow → Steps → Tools/APIs → Conditions → Result*.

### 1. How the Excel workflows are processed (1.5 min)
- Open the Excel file and point at the `Steps` column (arrow-separated) and `Decision_Logic`.
- Open `agent/registry.py`. It reads both sheets, splits steps on `→`, and merges the bindings.
- Open `config/workflow_bindings.yaml` at WF001. "Each Excel step, in order, is bound to a tool. Thresholds are
  config. Step labels come from Excel."
- Run `python -m agent validate` and `python -m agent list`. "The registry refuses a binding whose step count
  differs from Excel."

### 2. How the correct workflow is identified (1.5 min)
- Open `agent/router.py`, then `tool_schemas()`. "Every Excel row becomes an OpenAI function. Description from
  Excel, parameters from YAML, plus confidence and reasoning. `tool_choice=required` plus a
  `no_matching_workflow` escape."
- Run `python -m agent "Where is order ORD-1001?"` and point at *Selected workflow, Routing: llm-tool-calling,
  confidence, reasoning, extracted order_id*.
- Mention the offline fallback (TF-IDF plus regex), used with no key or if the API fails.

### 3. How the agent executes the workflow and calls tools (2 min)
- Open `agent/graph.py`. Run `python -m agent graph` (Mermaid): route → load → execute_step loop → finalize.
- Open `agent/executor.py`: `$ref` resolution, retries, `on_error`, halts.
- Open `agent/tools/__init__.py` (`@register_tool`), then one generic tool (`filter_rows`).
- Run `python -m agent "Which products need restocking?"` and walk the step table: each row is an Excel step,
  its tool, and the decision ("Rule current_stock < threshold → 6 products"). Point out SKU-1006 (stock equal to
  minimum) is correctly *not* flagged.

### 4. Conditions and error handling (2 min)
- **Ask before generating (WF007):** in the UI or interactive CLI, type *"Create a campaign brief for the new
  collection."* The agent asks for goal and dates. Answer *"Goal: drive launch sales, 2026-11-01 to
  2026-11-30, audience young professionals, promotion 15% off"* and the full brief appears (same workflow,
  remembered).
- **Not found → ask for another identifier (WF005):** *"Where is order ORD-9999?"*, then
  *"try priya.sharma@example.com"*.
- **Retries:** `SIMULATE_API_FAILURE=order_api:2 python -m agent "Where is order ORD-1003?"` shows 3 attempts,
  then success. With `SIMULATE_API_FAILURE=order_api` it fails cleanly with an explanation.
- **Don't invent (WF004):** `python -m agent "Generate SEO content for this product." --attach examples/attachments/product_wool_coat.json`.
  Point at `[MISSING: material]` and the length limits.
- **Escalation (WF009):** *"Assign a Kubernetes and Go migration task (40 hours) to a developer by 2026-10-10"*
  ends ESCALATED.

### 5. Working examples (2 min) – Streamlit
- `streamlit run app.py`. Run the remaining Excel test questions from the dropdown: WF002 (10% boundary: SKU-1006
  is exactly 10% and not flagged), WF003 (upload `data/vendor_files/vendor_acme_products.xlsx`: messy headers auto-mapped, invalid rows; without a file it asks for one), WF006 (Definite vs High,
  variants excluded), WF008, WF009 (ranking with reasons), WF010.
- Show `outputs/results.md`: all 32 recorded runs. Then run `pytest -q`: 84 passing.

### 6. Supporting an 11th workflow (1.5 min)
- Run `python scripts/demo_add_workflow.py`. It adds an Excel row and a YAML block (existing tools only),
  validates, and answers "Give me stock totals by product category" → WF011.
- "Zero Python changes. If a capability is new, it's one decorated function."
  Show `tests/test_extensibility.py`.

### 7. Key technical decisions (1 min)
- Declarative bindings rather than a free-form ReAct agent: deterministic business rules, auditable steps,
  testable. The LLM is used for understanding and language.
- LangGraph: explicit state machine, one Excel step per node pass, halts as edges, ready for checkpointing and
  human-in-the-loop.
- Safe expression evaluator: rules in config without `eval`.
- Offline mode: runnable without a key, reproducible tests, and resilient if the LLM is down.
- Self-observability: the agent's own runs are logged in WF010's format. Ask *"Show a performance report of this
  agent's own live runs."*
- Next steps: top-k pre-filtering for many workflows, checkpointer for multi-user memory, real API clients behind
  the same interface.
