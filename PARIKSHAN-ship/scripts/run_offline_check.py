#!/usr/bin/env python
"""Offline-operation check — PRD §5 SC-7 ("Full offline operation ... passes
with network adapter disabled") and Phase 7 DoD.

Rather than literally disabling the network adapter (impractical to automate
and to verify), this patches `socket.socket.connect`/`connect_ex` to detect
any attempted connection to a non-loopback address while the core pipeline
runs: loading cached data, computing risk scores, and answering assistant
questions via the whitelisted tools + rule-based routing + deterministic
fallback template. A genuine attempt to reach the internet raises
immediately, so this fails loudly rather than silently passing on a
pipeline that happens not to need the network THIS run.

Loopback (127.0.0.1 / ::1 / localhost) is allowed: Ollama itself is a local
HTTP server, and calling it is not a violation of "fully offline capable" —
the requirement is no dependency on an external/hosted service, not zero
sockets whatsoever. This check exercises only the fallback-template path
(no live Ollama call) since that is the pipeline guaranteed to still work
with zero network access at all, including loopback.

Usage: python scripts/run_offline_check.py
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


class OutboundConnectionError(RuntimeError):
    pass


def _guarded_connect(original):
    def _connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in _LOOPBACK_HOSTS:
            raise OutboundConnectionError(f"Blocked outbound connection attempt to {address!r}")
        return original(self, address)

    return _connect


def _install_network_guard() -> None:
    socket.socket.connect = _guarded_connect(socket.socket.connect)
    socket.socket.connect_ex = _guarded_connect(socket.socket.connect_ex)


def _exercise_pipeline() -> None:
    from paimana import config
    from paimana.assistant.llm import render_fallback, verify_numeric_fidelity
    from paimana.assistant.retriever import route_by_rules
    from paimana.assistant.tools import TOOL_REGISTRY
    from paimana.data.loader import load_processed_features, load_processed_projects

    print("Loading cached processed data...")
    load_processed_projects()
    load_processed_features()

    print("Reading precomputed risk/alert artifacts...")
    import pandas as pd

    pd.read_parquet(config.RISK_SCORES_PARQUET)
    pd.read_parquet(config.ALERTS_PARQUET)

    print("Exercising whitelisted assistant tools + rule routing + fallback narration...")
    questions = [
        "How many projects are at risk?",
        "What is the riskiest sector?",
        "Show me PRJ-00001",
        "What are the top 5 riskiest projects?",
    ]
    for question in questions:
        rule_result = route_by_rules(question)
        assert rule_result is not None, f"expected a rule match for {question!r}"
        tool_name, kwargs = rule_result
        kwargs_clean = {k: v for k, v in kwargs.items() if v is not None}
        tool_result = TOOL_REGISTRY[tool_name]["fn"](**kwargs_clean)
        answer = render_fallback(tool_name, tool_result)
        verified, unverified = verify_numeric_fidelity(answer, tool_result, question=question)
        assert verified, f"fidelity check failed offline for {question!r}: {unverified}"


def main() -> None:
    _install_network_guard()
    try:
        _exercise_pipeline()
    except OutboundConnectionError as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
    else:
        print("\nPASS: core pipeline (data load, risk artifacts, assistant tools, rule routing, "
              "deterministic narration) completed with zero outbound network connections.")


if __name__ == "__main__":
    main()
