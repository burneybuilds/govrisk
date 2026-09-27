"""The LLM Project Intelligence Assistant (Phase 7).

Anti-hallucination architecture (PRD §6.9): the LLM never computes or
invents a number. `tools.py` exposes a whitelisted set of pandas functions
that read the SAME cached artifacts the dashboard uses (never touching the
235MB models or training/predicting at request time); `retriever.py` routes
a natural-language question to one of those tools; `llm.py` asks a local
Ollama model to narrate the tool's verified output into prose, falling back
to a deterministic Jinja template — rendering the identical numbers — if
Ollama is unavailable, so this screen can never hard-fail during a demo.
"""
