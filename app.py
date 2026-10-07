"""Streamlit demo UI.   Run:  streamlit run app.py

Same agent as the CLI - the UI only renders the RunResult (selected workflow,
routing reasoning, executed steps with decisions, final result).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from agent import WorkflowAgent
from agent.llm import LLMClient
from agent.attachments import load_attachments
from agent.render import to_markdown

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Excel2Agent", page_icon="⚙️", layout="wide")


@st.cache_resource
def get_agent(offline: bool) -> WorkflowAgent:
    return WorkflowAgent(llm=LLMClient(offline=offline))


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("⚙️ Excel2Agent")
    offline = st.toggle("Offline mode (no LLM)", value=False,
                        help="Uses deterministic routing/fallbacks. Automatically on when OPENAI_API_KEY is not set.")
    agent = get_agent(offline)
    st.caption(f"LLM mode: **{agent.llm.mode}**")
    st.subheader("Workflows (from Excel)")
    for w in agent.registry.workflows.values():
        st.markdown(f"**{w.id}** {w.name}  \n<small>{w.trigger}</small>", unsafe_allow_html=True)
    if agent.registry.issues:
        st.warning("\n".join(f"{i.workflow_id}: {i.message}" for i in agent.registry.issues))
    if st.button("Reset conversation"):
        agent.reset()
        st.session_state.history = []

st.title("Excel2Agent")
st.caption("User request → Agent → Identify workflow → Workflow steps → Tools/APIs → Conditions → Final result")

cases = yaml.safe_load((ROOT / "examples" / "requests.yaml").read_text(encoding="utf-8"))
example_map: dict[str, tuple[str, list]] = {}
for c in cases:
    for t in c["turns"]:
        att = t.get("attach", [])
        label = t["request"] + (f"  📎 {Path(att[0]).name}" if att else "")
        example_map.setdefault(label, (t["request"], att))
examples = [""] + sorted(example_map)
col1, col2 = st.columns([3, 1])
with col1:
    picked = st.selectbox("Example requests", examples, index=0)
with col2:
    upload = st.file_uploader("Attach (csv/xlsx/json)", type=["csv", "xlsx", "json"])

if "history" not in st.session_state:
    st.session_state.history = []

typed = st.chat_input("Ask the agent…")
run_example = st.button("Run example", disabled=not picked)
prompt, example_attach = (typed, []) if typed else (example_map[picked] if run_example and picked else (None, []))

if prompt:
    attachments: dict = load_attachments([str(ROOT / a) for a in example_attach])
    if upload is not None:
        suffix = Path(upload.name).suffix.lower()
        if suffix == ".json":
            attachments = json.loads(upload.getvalue())
        else:
            tmp = Path(tempfile.mkdtemp()) / upload.name
            tmp.write_bytes(upload.getvalue())
            attachments = {"keywords_path" if "keyword" in upload.name.lower() else "file_path": str(tmp)}
    with st.spinner("Agent working…"):
        st.session_state.history.append(agent.run(prompt, attachments))

for r in reversed(st.session_state.history):
    with st.container(border=True):
        st.markdown(f"#### 🗣️ {r.request}")
        c = st.columns(4)
        c[0].metric("Selected workflow", r.workflow_id or "—", r.workflow_name or "")
        c[1].metric("Status", r.status.upper())
        c[2].metric("Confidence", f"{r.routing.confidence:.2f}" if r.routing else "—")
        c[3].metric("Steps", len(r.steps), f"{r.total_ms:.0f} ms", delta_color="off")
        if r.routing:
            st.caption(f"Routing via **{r.routing.method}** — {r.routing.reasoning}")
        params = {k: v for k, v in r.params.items() if v not in (None, "", [])}
        if params:
            st.code(json.dumps(params, indent=1, default=str), language="json")
        if r.steps:
            st.markdown("**Steps executed**")
            st.dataframe(pd.DataFrame([{
                "#": s.index, "Step (Excel)": s.label, "Tool": s.tool, "Status": s.status,
                "ms": s.duration_ms, "Attempts": s.attempts, "Result": s.summary,
                "Decisions": " | ".join(s.decisions)} for s in r.steps]), hide_index=True, width="stretch")
        if r.status == "needs_input":
            st.warning(r.message + "  \n_Reply in the chat box - the agent remembers this workflow._")
        elif r.status in ("failed", "no_match"):
            st.error(r.message)
        if r.report:
            st.markdown(to_markdown(r, ("report",)))
