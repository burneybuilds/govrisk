#!/usr/bin/env python
"""Live evaluation of the assistant against the golden question set — PRD
§7/Phase 7 task 6's literal DoD ask: "8 canonical questions ... automated
assertion that every quoted figure matches pandas ground truth," exercised
against the REAL Ollama model, not the deterministic fallback.

`tests/test_golden_questions.py` checks the SAME 8 questions but always
renders via `render_fallback` — fast, deterministic, no external process,
suitable for CI. This script is the complementary live check: it calls
`answer_question`, which prefers a real Ollama call and only drops to the
fallback if Ollama is unreachable, slow, or errors. Run it after `ollama
serve` is up and `qwen2.5:7b-instruct` is pulled (see README) to confirm the
live narration is numerically faithful, not just the template.

Usage: python scripts/run_assistant_eval.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from tests.test_golden_questions import GOLDEN_QUESTIONS  # noqa: E402

from paimana.assistant.llm import answer_question, verify_numeric_fidelity  # noqa: E402
from paimana.assistant.retriever import route_question  # noqa: E402
from paimana.assistant.tools import TOOL_REGISTRY  # noqa: E402


def main() -> None:
    print(f"Evaluating {len(GOLDEN_QUESTIONS)} golden questions against the live assistant "
          "(Ollama if reachable, else fallback)...\n")

    results = []
    for question, expected_tool in GOLDEN_QUESTIONS:
        tool_name, kwargs, routing_method = route_question(question)
        kwargs_clean = {k: v for k, v in kwargs.items() if v is not None}
        tool_result = TOOL_REGISTRY[tool_name]["fn"](**kwargs_clean)

        response = answer_question(question, tool_name, tool_result, routing_method)
        verified, unverified = verify_numeric_fidelity(response.answer, tool_result, question=question)
        routed_ok = tool_name == expected_tool
        results.append((question, routed_ok, verified, unverified, response.source))

        status = "PASS" if (routed_ok and verified) else "FAIL"
        print(f"[{status}] {question!r}")
        print(f"    source={response.source}, routed_ok={routed_ok} (tool={tool_name}), "
              f"verified={verified}, unverified={unverified}")
        print(f"    answer: {response.answer[:200]}{'...' if len(response.answer) > 200 else ''}")
        print()

    n_pass = sum(1 for _, routed_ok, verified, _, _ in results if routed_ok and verified)
    n_ollama = sum(1 for *_r, source in results if source == "ollama")
    print(f"Summary: {n_pass}/{len(results)} passed. {n_ollama}/{len(results)} answered by live Ollama "
          f"({len(results) - n_ollama} fell back to the deterministic template).")

    if n_pass < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
