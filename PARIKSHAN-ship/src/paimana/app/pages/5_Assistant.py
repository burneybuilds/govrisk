"""LLM Project Intelligence Assistant — PRD §7/Phase 7, §6.9.

Anti-hallucination architecture: every answer is the LLM NARRATING a
whitelisted pandas tool's verified output, never a number it computed or
recalled itself. If Ollama is unavailable, slow, or errors, a deterministic
Jinja template renders the identical numbers — this screen cannot hard-fail
during a demo. The tool invoked and its raw JSON are always shown alongside
the prose, by design (PRD §7/Phase 7 task 5) — transparency over polish.

Defensive import note: `torch` (sentence-transformers' dependency) must be
imported before pandas/numpy on this machine to avoid a DLL-load conflict
found during Phase 7 build (see `paimana/assistant/retriever.py`'s
top-of-file comment and HANDOFF.md). This page imports it first for the
case where a user navigates here directly; if Home.py already ran first in
this Streamlit session (the common case), pandas is already loaded and the
embedding layer gracefully degrades to rule-only routing regardless — never
a crash, just a visibly-labelled "default_fallback" routing method.

The preload below catches broad `Exception`, not just `ImportError`: the
actual DLL conflict raises `OSError: [WinError 1114] ... c10.dll`, which a
narrower `except ImportError` does NOT catch — this exact gap crashed this
page live (a real `OSError` traceback rendered in the browser) during the
Phase 7 mandatory live-UI check, caught only by actually loading the page,
not by any unit test. See the identical comment and fix in
`paimana/assistant/retriever.py`.
"""

from __future__ import annotations

try:
    import torch as _torch_preload  # noqa: F401
except Exception:  # noqa: BLE001 - see comment above; must not crash the page
    pass

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit as st

from paimana.app.common import render_synthetic_banner
from paimana.assistant.llm import answer_question
from paimana.assistant.retriever import route_question
from paimana.assistant.tools import TOOL_REGISTRY

st.set_page_config(page_title="PARIKSHAN — Assistant", page_icon="💬", layout="wide")

st.title("💬 LLM Project Intelligence Assistant")
render_synthetic_banner()

st.caption(
    "This assistant only ever **narrates** numbers computed by a whitelisted pandas tool — it "
    "never computes or estimates a figure itself. The tool invoked and its raw verified data are "
    "always shown below the answer. If the local Ollama model is unavailable, a deterministic "
    "template renders the identical numbers."
)

EXAMPLE_QUESTIONS = [
    "How many projects are at risk?",
    "What is the riskiest sector?",
    "Show me PRJ-00001",
    "What are the top 10 riskiest projects?",
    "Did ML beat conventional statistics?",
    "How early would we have caught severe overruns?",
]

if "assistant_history" not in st.session_state:
    st.session_state.assistant_history = []

with st.expander("Example questions", expanded=len(st.session_state.assistant_history) == 0):
    cols = st.columns(2)
    for i, example in enumerate(EXAMPLE_QUESTIONS):
        if cols[i % 2].button(example, key=f"example_{i}", use_container_width=True):
            st.session_state.pending_question = example

question = st.text_input(
    "Ask a question about the portfolio",
    value=st.session_state.pop("pending_question", ""),
    placeholder="e.g. Which sector has the worst cost overrun?",
)

if st.button("Ask", type="primary") and question.strip():
    with st.spinner("Routing to a verified data tool, then asking the local model to narrate it..."):
        tool_name, kwargs, routing_method = route_question(question)
        kwargs_clean = {k: v for k, v in kwargs.items() if v is not None}
        try:
            tool_result = TOOL_REGISTRY[tool_name]["fn"](**kwargs_clean)
            tool_error = None
        except ValueError as exc:
            tool_result = {}
            tool_error = str(exc)

        if tool_error is None:
            response = answer_question(question, tool_name, tool_result, routing_method)
            st.session_state.assistant_history.insert(0, response)
        else:
            st.error(f"Couldn't answer that: {tool_error}")

for response in st.session_state.assistant_history:
    with st.chat_message("assistant"):
        st.markdown(response.answer)
        source_label = (
            "🤖 Ollama (Qwen2.5-7B)" if response.source == "ollama" else "📋 Deterministic fallback"
        )
        method_label = {
            "rule": "keyword rule",
            "narrative_search": "project narrative search (MiniLM)",
            "embedding": "semantic (MiniLM) match",
            "default_fallback": "no confident match — default",
        }[response.routing_method]
        st.caption(f"{source_label} · Tool: `{response.tool_used}` ({method_label})")
        if response.ollama_answer_rejected:
            st.caption(
                "⚠️ The local model's answer was rejected because it stated a number that couldn't "
                "be verified against the tool's data — showing the deterministic template instead."
            )
        with st.expander("Raw verified data used for this answer"):
            st.json(response.tool_result)

if not st.session_state.assistant_history:
    st.info("Ask a question above, or click one of the examples.", icon="💡")
