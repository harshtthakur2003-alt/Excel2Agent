# Adding a workflow (the 11th and beyond)

This guide walks through a worked example: **WF011 Category Stock Summary**.

## 1. Add the Excel row

In `workflows/AI_Agent_Workflow_Assessment.xlsx`, sheet **Workflows**:

| Workflow_ID | Workflow_Name | Trigger | Inputs | Steps | Decision_Logic | Tools_Required | Expected_Output |
|---|---|---|---|---|---|---|---|
| WF011 | Category Stock Summary | User asks for stock totals by product category | Product inventory CSV; low-stock category threshold | Load inventory → aggregate stock by category → flag low-stock categories → generate category summary | Flag a category when its total stock is below 50 units | CSV reader; calculator | Stock per category with low-stock flags |

You can also add a test question to the **Test_Questions** sheet.

## 2. Bind each step to a tool

Add one entry per Excel step, in the same order. The full file is
[`examples/wf011_extension/wf011_binding.yaml`](../examples/wf011_extension/wf011_binding.yaml):

```yaml
  WF011:
    keywords: [category, categories, stock totals, summary]   # optional, helps the offline router
    settings: {category_threshold: 50}                       # decision thresholds live in config
    steps:
      - tool: load_table                                     # Load inventory
        args: {path: data/inventory.csv}
        output: inventory
      - tool: aggregate                                      # Aggregate stock by category
        args: {rows: $data.inventory, group_by: [category],
               metrics: {total_stock: {op: sum, field: current_stock}, products: {op: count}}}
        output: by_category
      - tool: compute_columns                                # Flag low-stock categories
        args: {rows: $data.by_category, variables: {limit: $settings.category_threshold},
               columns: {low_stock: total_stock < limit}}
        output: flagged
      - tool: filter_rows                                    # Generate category summary
        args: {rows: $data.flagged, condition: low_stock, label: categories}
        output: low
    report:
      title: Category stock summary
      vars: {low: $data.low}
      computed: {n: len(low)}
      summary: "{n} category(ies) below the threshold."
      tables:
        - {title: Stock by category, rows: $data.flagged, columns: [category, products, total_stock, low_stock]}
```

Useful binding features:

| Key | Purpose |
|---|---|
| `params.<name>` | What to extract from the request (`type`, `description`, `required`, `default`, `enum`, `pattern`, `keywords`, `llm`). This becomes the LLM function schema |
| `$params.x` / `$settings.x` / `$data.key` / `$request` | References resolved at runtime |
| `retries`, `on_error: continue`, `when: <expr>` | Per-step error and condition policy |
| `validate_params` tool | "If X is missing, ask the user" rules |
| `require_rows` tool | "If nothing found, ask / stop" rules |
| `llm_generate` / `llm_classify` | LLM steps with output validation and a named offline fallback |

## 3. Only if a capability is genuinely new: write a tool

```python
# agent/tools/my_tools.py  (auto-discovered, no imports to update)
from ..models import StepOutcome
from . import ToolContext, register_tool

@register_tool("currency_convert", "calculator", "Convert a price column to another currency")
def currency_convert(ctx: ToolContext, rows: list, field: str, rate: float) -> StepOutcome:
    out = [{**r, f"{field}_converted": round(float(r[field]) * rate, 2)} for r in rows]
    return StepOutcome(out, f"Converted {len(out)} prices", decisions=[f"rate = {rate}"])
```

## 4. Validate and run

```bash
python -m agent validate                         # step counts match Excel, tools exist
python -m agent "Give me stock totals by product category"
```

Nothing else changes: the LLM function list, the offline router index, the graph, the CLI, the UI and the
output rendering all pick up the new workflow. To try it without editing the real files, run
`python scripts/demo_add_workflow.py` (or add `--apply` to write the changes for real).
`tests/test_extensibility.py` asserts this end to end.
