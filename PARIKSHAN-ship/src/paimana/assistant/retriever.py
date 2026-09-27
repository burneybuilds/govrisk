"""Intent routing — PRD §7/Phase 7 task 3.

Two layers, tried in order:

1. **Rules first** — fast, deterministic keyword/regex matching that
   covers the common, well-phrased questions without any ML inference at
   all. Most real questions ("which sector is riskiest", "show me PRJ-
   00123", "top 10 risky projects") match here.
2. **MiniLM embedding fallback** — for fuzzier phrasing that doesn't hit a
   rule, embed the question and each tool's description with a local
   `all-MiniLM-L6-v2` model and pick the closest by cosine similarity.

A THIRD, separate capability — resolving a question that names a project
by description rather than by ID ("the fertilizer project in Kerala that's
behind schedule") — uses a brute-force numpy cosine search over
precomputed per-project narrative embeddings (PRD §3.1: no vector DB; see
Phase 1 HANDOFF.md for why ChromaDB was dropped). The corpus (~1,981 short
narratives) and its embeddings are built ONCE by
`scripts/run_assistant_index.py`, never at request time.
"""

from __future__ import annotations

# MUST be the first import in this file, before numpy/pandas: on this
# machine, importing torch AFTER numpy/pandas have already loaded their own
# BLAS/OpenMP runtime causes `OSError: [WinError 1114] ... c10.dll` (a DLL
# init failure, not a missing package — found and diagnosed during Phase 7
# build, see HANDOFF.md). Importing torch first avoids the conflict
# entirely. This module still degrades gracefully via
# `EmbeddingUnavailableError` if torch is unavailable or this ordering
# doesn't help in some other process (e.g. numpy/pandas were already
# imported by an earlier, unrelated module before this file was reached —
# the full `pytest` suite hits exactly this: an earlier-collected test
# module imports pandas before this file is ever reached, so the preload
# below raises the SAME `OSError`, not `ImportError` — caught broadly here
# for that reason, deliberately, not because the failure mode is unknown).
try:
    import torch as _torch_preload  # noqa: F401
except Exception:  # noqa: BLE001 - see comment above; must not crash module import
    pass

import re

import numpy as np
import pandas as pd

from paimana import config
from paimana.assistant.tools import TOOL_REGISTRY

_PROJECT_ID_PATTERN = re.compile(r"PRJ-\d{5}", re.IGNORECASE)
_NUMBER_PATTERN = re.compile(r"\b(\d{1,3})\b")
_SEVERITY_WORDS = {"critical": "Critical", "high": "High", "medium": "Medium"}

# Longer names first so "Uttar Pradesh" doesn't get shadowed by a shorter
# substring match, and so multi-word sector names match before their
# shorter component words could confuse a naive scan.
_SECTORS_BY_LENGTH = sorted(config.SECTORS, key=len, reverse=True)
_STATES_BY_LENGTH = sorted(config.STATES, key=len, reverse=True)


def _find_all_sectors(text: str) -> list[str]:
    lowered = text.lower()
    return [s for s in _SECTORS_BY_LENGTH if s.lower() in lowered]


def _find_state(text: str) -> str | None:
    lowered = text.lower()
    for s in _STATES_BY_LENGTH:
        if s.lower() in lowered:
            return s
    return None


def _find_target(text: str) -> str | None:
    lowered = text.lower()
    if "severe" in lowered:
        return "y_severe"
    if "cost overrun" in lowered or "cost-overrun" in lowered:
        return "y_cost_overrun"
    if "time overrun" in lowered or "schedule" in lowered or "delay" in lowered:
        return "y_time_overrun"
    return None


def route_by_rules(question: str) -> tuple[str, dict] | None:
    """Return (tool_name, kwargs) if a deterministic rule matches, else None."""
    lowered = question.lower()

    project_match = _PROJECT_ID_PATTERN.search(question)
    if project_match:
        return "project_detail", {"project_id": project_match.group(0).upper()}

    if any(
        w in lowered
        for w in ("backtest", "lead time", "lead-time", "caught early", "early enough", "how early")
    ) or ("early" in lowered and "catch" in lowered):
        return "backtest_summary", {}

    if any(w in lowered for w in ("delay reason", "why are projects", "most common issue", "root cause")):
        return "delay_reason_breakdown", {}

    if any(w in lowered for w in ("bake-off", "bakeoff", "significant", "beat conventional", "ml vs")) or (
        "model" in lowered and ("accuracy" in lowered or "better" in lowered or "compare" in lowered)
    ):
        return "model_bakeoff_summary", {"target": _find_target(question)}

    if "alert" in lowered or "flagged" in lowered:
        severity = next((v for k, v in _SEVERITY_WORDS.items() if k in lowered), None)
        return "alert_digest", {"severity": severity, "limit": 10}

    sectors_mentioned = _find_all_sectors(question)
    if "compare" in lowered and len(sectors_mentioned) >= 2:
        return "compare_sectors", {"sector_a": sectors_mentioned[0], "sector_b": sectors_mentioned[1]}

    is_superlative = any(w in lowered for w in ("top", "riskiest", "highest risk", "worst", "which"))

    # "riskiest SECTOR" / "which sector is worst" — a request to RANK
    # sectors, distinct from a question that names one specific sector
    # (e.g. "Railways") handled below. Checked first: the literal word
    # "sector"/"state" here is a category name, not one of the actual
    # config.SECTORS/STATES values `_find_all_sectors` looks for.
    if is_superlative and "sector" in lowered and not sectors_mentioned:
        return "sector_risk_summary", {"sector": None}
    if is_superlative and "state" in lowered and not _find_state(question):
        return "state_risk_summary", {"state": None}

    if is_superlative and ("project" in lowered or "sector" not in lowered):
        if sectors_mentioned:
            return "sector_risk_summary", {"sector": sectors_mentioned[0]}
        number_match = _NUMBER_PATTERN.search(question)
        k = int(number_match.group(1)) if number_match else 10
        return "top_risk_projects", {"k": k}

    if sectors_mentioned:
        return "sector_risk_summary", {"sector": sectors_mentioned[0]}

    state_mentioned = _find_state(question)
    if state_mentioned and "state" in lowered:
        return "state_risk_summary", {"state": state_mentioned}

    if any(w in lowered for w in ("portfolio", "overview", "how many projects", "total")):
        return "portfolio_summary", {}

    return None


# --------------------------------------------------------------------------
# MiniLM embedding fallback (lazy-loaded singleton — the model is only
# loaded into memory the first time a question doesn't match a rule)
# --------------------------------------------------------------------------
_embedding_model = None
_tool_description_embeddings: np.ndarray | None = None
_tool_names: list[str] = []


class EmbeddingUnavailableError(RuntimeError):
    """Raised when the local MiniLM model can't be loaded (missing package,
    or — a real issue hit during Phase 7 build — a broken torch install on
    this specific Windows machine, DLL load failure on `c10.dll`, most
    commonly caused by a missing Visual C++ Redistributable). Callers must
    catch this and degrade gracefully to the rule layer's default rather
    than letting a broken optional dependency take down question-answering
    entirely — the same defense-in-depth principle as `llm.py`'s Ollama
    fallback.
    """


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:  # noqa: BLE001 - deliberately broad, see class docstring
            raise EmbeddingUnavailableError(f"Could not load the embedding model: {exc}") from exc
    return _embedding_model


def _get_tool_description_embeddings() -> tuple[np.ndarray, list[str]]:
    global _tool_description_embeddings, _tool_names
    if _tool_description_embeddings is None:
        model = _get_embedding_model()
        _tool_names = list(TOOL_REGISTRY)
        descriptions = [TOOL_REGISTRY[name]["description"] for name in _tool_names]
        embeddings = np.asarray(model.encode(descriptions), dtype=np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        _tool_description_embeddings = embeddings / np.clip(norms, 1e-8, None)
    return _tool_description_embeddings, _tool_names


def route_by_embedding(question: str) -> tuple[str, dict]:
    """Semantic fallback: nearest tool description by cosine similarity.
    Always returns something (defaults to portfolio_summary for kwargs) —
    callers should still show which tool was used so a bad match is visible
    rather than silently wrong.
    """
    embeddings, tool_names = _get_tool_description_embeddings()
    model = _get_embedding_model()
    query_vec = np.asarray(model.encode([question]), dtype=np.float32)[0]
    query_vec = query_vec / max(np.linalg.norm(query_vec), 1e-8)

    similarities = embeddings @ query_vec
    best_idx = int(np.argmax(similarities))
    tool_name = tool_names[best_idx]

    # Best-effort kwargs extraction for the chosen tool, same helpers as
    # the rule layer — an embedding match still benefits from a mentioned
    # sector/state/project id if the question happens to contain one.
    kwargs: dict = {}
    params = TOOL_REGISTRY[tool_name]["params"]
    if "sector" in params:
        sectors = _find_all_sectors(question)
        kwargs["sector"] = sectors[0] if sectors else None
    if "state" in params:
        kwargs["state"] = _find_state(question)
    if "project_id" in params:
        match = _PROJECT_ID_PATTERN.search(question)
        if match:
            kwargs["project_id"] = match.group(0).upper()
    if "target" in params:
        kwargs["target"] = _find_target(question)
    if "k" in params:
        number_match = _NUMBER_PATTERN.search(question)
        kwargs["k"] = int(number_match.group(1)) if number_match else 10
    if "limit" in params:
        kwargs["limit"] = 10
    if "severity" in params:
        kwargs["severity"] = next((v for k, v in _SEVERITY_WORDS.items() if k in question.lower()), None)

    return tool_name, kwargs


_NARRATIVE_SEARCH_MIN_SCORE = 0.5


def route_question(question: str) -> tuple[str, dict, str]:
    """Route a question to (tool_name, kwargs, method) where method is
    "rule", "narrative_search", "embedding", or "default_fallback" —
    surfaced in the UI so a fuzzy/uncertain match is visibly distinguishable
    from a confident, deterministic one, and so an embedding-layer failure
    (see `EmbeddingUnavailableError`) is honestly labelled rather than
    silently passed off as a real semantic match.
    """
    rule_result = route_by_rules(question)
    if rule_result is not None:
        return rule_result[0], rule_result[1], "rule"

    # A question that names a project by DESCRIPTION rather than by ID or
    # by sector/state alone (PRD §3.1's "vector search over project
    # narratives") — tried before the generic tool-description match, since
    # it resolves to something more specific and useful when the user is
    # clearly asking about one project.
    if "project" in question.lower():
        try:
            matches = find_project_by_description(question, top_k=1)
            if matches and matches[0]["score"] >= _NARRATIVE_SEARCH_MIN_SCORE:
                return "project_detail", {"project_id": matches[0]["project_id"]}, "narrative_search"
        except (FileNotFoundError, EmbeddingUnavailableError):
            pass

    try:
        tool_name, kwargs = route_by_embedding(question)
        return tool_name, kwargs, "embedding"
    except EmbeddingUnavailableError:
        return "portfolio_summary", {}, "default_fallback"


# --------------------------------------------------------------------------
# Project narrative search (resolving a project named by description)
# --------------------------------------------------------------------------
def find_project_by_description(query: str, top_k: int = 1) -> list[dict]:
    """Brute-force cosine search over precomputed project narrative
    embeddings — returns the top-k matching {project_id, narrative, score}.
    Requires `scripts/run_assistant_index.py` to have been run.
    """
    narratives_path = config.ARTIFACTS_METRICS_DIR / "project_narratives.parquet"
    embeddings_path = config.ARTIFACTS_METRICS_DIR / "project_narrative_embeddings.npy"
    if not narratives_path.exists() or not embeddings_path.exists():
        raise FileNotFoundError(
            "Project narrative index not found — run `python scripts/run_assistant_index.py` first."
        )

    narratives = pd.read_parquet(narratives_path)
    embeddings = np.load(embeddings_path)

    model = _get_embedding_model()
    query_vec = np.asarray(model.encode([query]), dtype=np.float32)[0]
    query_vec = query_vec / max(np.linalg.norm(query_vec), 1e-8)

    similarities = embeddings @ query_vec
    top_idx = np.argsort(-similarities)[:top_k]
    return [
        {
            "project_id": narratives.iloc[i]["project_id"],
            "narrative": narratives.iloc[i]["narrative"],
            "score": float(similarities[i]),
        }
        for i in top_idx
    ]
