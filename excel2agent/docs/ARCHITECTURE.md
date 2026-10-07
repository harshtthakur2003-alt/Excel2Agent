# Architecture and technical decisions

## 1. Core idea: workflows are data, the agent is generic

The assignment asks for a system where adding an 11th workflow takes minimal code. So the design separates three
concerns:

| Concern | Lives in | Changes when… |
|---|---|---|
| **What** a workflow is (steps, rules, I/O) | Excel (`workflows/…xlsx`) | the business process changes |
| **How** each step runs (tool + args, thresholds, report layout) | YAML (`config/workflow_bindings.yaml`) | a workflow is added or tuned |
| **Capabilities** (read CSV, compare, call API, call LLM) | Python tools (`agent/tools/`) | a new capability is needed |

The agent itself (router, graph, executor, renderers) does not know any workflow by name. Workflow IDs appear in
`agent/` only in docstrings and comments, never in logic.

### Why Excel plus YAML, not Excel alone?

The Excel `Steps` column is prose ("compare current stock with minimum threshold"), not an executable spec.
There are two ways to execute it:

- **Let an LLM improvise each step at runtime** (a ReAct agent with all tools). This is flexible but not
  deterministic, hard to test, and unreliable for exact business rules such as "exceeds 10%" or "< minimum".
  It also hides which step ran.
- **Bind each Excel step to a tool once, declaratively.** This is what I chose. The step names and order still
  come from Excel. The registry refuses to run a workflow whose binding has a different number of steps, so the
  two cannot silently drift apart.

The LLM is used where it adds value: understanding the request (routing and parameter extraction) and the
language-heavy steps (product copy, campaign messaging and channels, intent classification, skill extraction).
Arithmetic and rule evaluation stay deterministic.

## 2. Agent graph (LangGraph)

```
START → route_request ─┬─(no match)──────────────────────────→ finalize → END
                       └→ load_workflow ─┬─(not executable)──→ finalize
                                         └→ execute_step ⟲ (one Excel step per pass)
                                                  └─(done | needs_input | escalated | failed)→ finalize
```

- **Why LangGraph:** the flow is an explicit state machine with conditional edges. Each step becomes a visible
  graph iteration, which gives a clean trace, and the state (`params`, `data`, `steps`, `status`) is one typed
  dict. Running one step per node pass, rather than all steps inside a single node, means halts and failures are
  handled by graph edges instead of nested `if` statements. It also lets the graph be checkpointed or streamed
  later if needed.
- **Follow-ups:** when a run ends `needs_input`, the agent keeps `{workflow_id, params, request, missing}`. On
  the next message the router knows a question is pending. The answer is merged in, and the re-asked fields are
  replaced (a new email replaces an unknown order ID). The original request text is preserved, so "new
  collection" from turn 1 is still known in turn 2.

## 3. Workflow selection

### LLM mode: tool calling

Each workflow is turned into an OpenAI function automatically:

- `name`: `WF005_customer_order_status`
- `description`: built from the Excel columns (name, trigger, inputs, decision logic, expected output)
- `parameters`: built from the YAML `params`, plus `confidence` and `reasoning`

A `no_matching_workflow` function handles out-of-scope requests, and `tool_choice="required"` forces a decision.
A single call therefore performs **selection, parameter extraction and justification**. The system prompt forbids
inventing values. That matters because several workflows have rules like "if goal or dates are missing, ask".
File-path parameters are hidden from the model (`llm: false`); they come only from attachments or defaults, so the
model cannot hallucinate a path.

### Offline mode

TF-IDF cosine similarity is computed over each workflow's Excel text plus a few YAML keywords. Parameters come
from the regex and keyword maps declared on each parameter. Confidence combines the absolute score and the margin
over the runner-up, and a minimum score rejects out-of-scope requests. This mode is used without an API key,
and also automatically if an OpenAI call fails.

*Trade-off:* the lexical router cannot extract free-text parameters as well as an LLM (a campaign goal written
as prose, for example). The regex patterns cover the documented formats, and the LLM mode covers the rest.

## 4. Step execution, conditions and errors

`executor.run_step` is the only code that runs a step:

1. Resolve args: `$params.x`, `$settings.x`, `$data.<previous output>`, `$request`.
2. Evaluate `when:` and skip the step if it is false.
3. Call the tool, with `retries: n` for transient `ToolError`s.
4. On final failure: `on_error: fail` stops the run with *"Step 2 'Search order data' failed: …"*;
   `continue` records the error and moves on.
5. The tool returns a `StepOutcome(value, summary, decisions, halt, run_status)`:
   - `decisions` is the human-readable reasoning shown under each step ("Rule `current_stock < threshold` → 6
     products").
   - `halt=Halt("needs_input", question)` stops the run and asks the user.
   - `run_status="escalated"` flags the run without stopping it, so a summary is still produced (WF009).

Decision rules are expressions evaluated by a small AST interpreter (`agent/expressions.py`). It supports
arithmetic, comparisons, boolean logic and a whitelist of functions. There is no attribute access, import or
arbitrary call, so it is safe to keep rules in config and change thresholds without code changes. Comparisons
with missing values evaluate to `False` instead of crashing.

Error handling, by layer:

| Layer | Behaviour |
|---|---|
| Input | `validate_params` and `validate_identifier` ask for missing or invalid inputs (dates are parsed and ordered) |
| Data | Missing file, missing columns, or unrecognised headers fail with an actionable message |
| External API | Retries with backoff. Persistent outage → clean failure. Optional API (shipment) → degrade |
| LLM | Two attempts. Invalid JSON or labels → deterministic fallback. Length violations → one corrective re-ask, then trim |
| Unexpected bug in a tool | Caught per step and reported as a step failure, never a stack trace to the user |
| Logging | Every run is appended to `logs/`. A logging failure never breaks a run |

## 5. Tools

There are 41 tools, auto-discovered from `agent/tools/`:

- **Generic, reused across workflows:** `load_table(s)`, `compute_columns` (calculator), `filter_rows`,
  `partition_rows`, `join_tables`, `dedupe_rows`, `annotate_errors`, `aggregate`, `validate_params`,
  `require_rows`, `export_table`, `build_report`, `llm_generate`, `llm_classify`.
  WF001, WF002, WF003 and WF008 are composed mostly from these, and so is the WF011 demo.
- **Domain-specific:** order and shipment APIs, duplicate scoring, task ranking, log analysis, campaign planning.

They are domain-specific only where the logic doesn't reduce cleanly to generic operations (union-find
grouping, for example). Each is still a small, separately testable function.

## 6. Output contract

Every run returns a `RunResult` containing: request, status, routing (workflow, method, confidence, reasoning,
candidates), params, steps (label from Excel, tool, status, duration, attempts, summary, decisions, error),
report, message and LLM mode. The CLI, the Streamlit UI, `outputs/results.md` and `--json` all render this same
object. The run log uses the same schema as the sample execution logs, so WF010 can report on the agent's own
runs ("Show a performance report of this agent's own live runs").

## 7. Scalability notes and next steps

- **Many workflows (50+):** the router sends every workflow as a function. Beyond roughly 30, I'd pre-filter to
  the top-k candidates with the lexical or embedding index (already computed) and only send those to the LLM.
- **Persistence and concurrency:** follow-up memory is per `WorkflowAgent` instance. For a multi-user service,
  move it to a LangGraph checkpointer keyed by session ID.
- **Real APIs:** replace `services/mock_apis.py` with HTTP clients behind the same interface. The tools and
  bindings don't change.
- **Human-in-the-loop:** `escalated` and `needs_input` are natural interrupt points for LangGraph `interrupt()`.
- **Validation in CI:** `python -m agent validate` returns a non-zero exit code if the Excel and YAML disagree.
