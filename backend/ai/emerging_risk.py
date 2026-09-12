"""Emerging-risk detection from project updates.

The deterministic risk engine covers predefined categories; this module
surfaces risks that those rules may miss by reading the live project
update log. Detection is keyword-based (deterministic, explainable) and
optionally enriched by the LLM, which fills in OTHER categories with
free labels. Languages: English keywords for the MVP demo.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional

from config import ai_logger
from ai.schemas import EmergingRiskResult, UpdateAnalysisResult

CATEGORIES = (
    "STAKEHOLDER_CONFLICT", "COMMUNITY_OPPOSITION", "CONTRACTOR_DISPUTE",
    "DESIGN_CHANGE", "PROCUREMENT_DISRUPTION", "RESOURCE_SHORTAGE",
    "REGULATORY_CHANGE", "LAND_ACQUISITION", "INTER_DEPARTMENT_COORDINATION",
    "FUNDING_ISSUE", "TECHNICAL_COMPLEXITY", "ENVIRONMENTAL_CONCERN",
    "POLITICAL_OR_ADMINISTRATIVE_DEPENDENCY", "OTHER",
)

# category -> (keywords, title, recommended actions, impact areas)
RULES = {
    "STAKEHOLDER_CONFLICT": {
        "keywords": ["stakeholder objection", "objection", "stakeholder protest",
                     "residents have objected", "community objection"],
        "title": "Stakeholder coordination risk",
        "actions": ["Initiate stakeholder resolution meeting",
                    "Create an issue-resolution plan with the district authority"],
        "impact": ["Schedule", "Approval cycles"],
    },
    "COMMUNITY_OPPOSITION": {
        "keywords": ["protest", "demonstration", "residents opposed", "public agitation",
                     "local residents", "agitation"],
        "title": "Community opposition",
        "actions": ["Engage community leaders and schedule a public hearing",
                    "Prepare a communication plan addressing local concerns"],
        "impact": ["Schedule", "Land release"],
    },
    "CONTRACTOR_DISPUTE": {
        "keywords": ["contractor dispute", "arbitration", "contract dispute",
                     "payment dispute", "contractor threatening", "breach of contract"],
        "title": "Contractor dispute",
        "actions": ["Escalate to the contract-management cell",
                    "Convene a dispute-resolution meeting within 7 days"],
        "impact": ["Schedule", "Cost"],
    },
    "DESIGN_CHANGE": {
        "keywords": ["design revision", "design change", "rework", "revised design",
                     "change order", "scope change"],
        "title": "Design change / scope variation",
        "actions": ["Freeze the design baseline",
                    "Impact-assess cost and time before approving further changes"],
        "impact": ["Cost", "Schedule"],
    },
    "PROCUREMENT_DISRUPTION": {
        "keywords": ["procurement delayed", "procurement delay", "supplier delay",
                     "vendor delay", "import delay", "delivery delay", "order delayed",
                     "tender delayed", "bidding"],
        "title": "Procurement disruption",
        "actions": ["Identify alternative suppliers",
                    "Escalate the procurement bottleneck to the finance cell"],
        "impact": ["Schedule", "Material availability"],
    },
    "RESOURCE_SHORTAGE": {
        "keywords": ["material shortage", "labour shortage", "manpower shortage",
                     "equipment unavailability", "skill shortage", "shortage of"],
        "title": "Resource shortage",
        "actions": ["Re-plan resource allocation",
                    "Source replacement vendors for the constrained resource"],
        "impact": ["Progress", "Schedule"],
    },
    "REGULATORY_CHANGE": {
        "keywords": ["regulation change", "new regulation", "policy change",
                     "compliance change", "statutory direct"], 
        "title": "Regulatory change",
        "actions": ["Review compliance impact with the legal cell",
                    "Update project controls for the new regulation"],
        "impact": ["Scope", "Cost"],
    },
    "LAND_ACQUISITION": {
        "keywords": ["land acquisition", "land compensation", "land transfer",
                     "rehabilitation and resettlement", "rehabilitation plan",
                     "r&r plan", "land possession", "acquire land", "revenue records"],
        "title": "Land acquisition delay",
        "actions": ["Escalate land cases to the revenue department",
                    "Raise compensation disbursement issues with the district collector"],
        "impact": ["Schedule", "Clearance"],
    },
    "INTER_DEPARTMENT_COORDINATION": {
        "keywords": ["cross-department", "interdepartmental", "inter-department",
                     "coordination delay", "approval awaited", "pending approval",
                     "awaiting clearance", "department coordination"],
        "title": "Inter-department coordination delay",
        "actions": ["Set up a monthly inter-department review",
                    "Assign a nodal coordinator for pending approvals"],
        "impact": ["Schedule", "Clearance"],
    },
    "FUNDING_ISSUE": {
        "keywords": ["funding delay", "budget sanction", "fund release", "financial stress",
                     "funding approval", "budget cut", "cash flow", "expenditure freeze"],
        "title": "Funding / budget risk",
        "actions": ["Request fund release with the finance department",
                    "Prepare a revised cash-flow plan for the next quarter"],
        "impact": ["Progress", "Contractor payments"],
    },
    "TECHNICAL_COMPLEXITY": {
        "keywords": ["technical complexity", "design complexity", "technical challenge",
                     "unforeseen geology", "utility shifting", "geotechnical",
                     "unexpected site condition"],
        "title": "Technical / site complexity",
        "actions": ["Commission a technical review board",
                    "Allocate contingency for the unforeseen condition"],
        "impact": ["Schedule", "Cost"],
    },
    "ENVIRONMENTAL_CONCERN": {
        "keywords": ["environmental clearance", "environment impact", "green clearance",
                     "forest clearance", "wildlife clearance", "environmental concern"],
        "title": "Environmental clearance concern",
        "actions": ["Fast-track the environmental impact assessment",
                    "Liaise with the forest/environment department directly"],
        "impact": ["Schedule", "Approval"],
    },
    "POLITICAL_OR_ADMINISTRATIVE_DEPENDENCY": {
        "keywords": ["ministerial approval", "cabinet approval", "political approval",
                     "election impasse", "transfer of official", "administrative delay"],
        "title": "Political / administrative dependency",
        "actions": ["Flag the dependency in the monitoring committee note",
                    "Align the approval timeline to the administrative calendar"],
        "impact": ["Schedule", "Approval"],
    },
}


def _match_rule(text: str):
    lowered = (text or "").lower()
    for category, rule in RULES.items():
        for keyword in rule["keywords"]:
            if keyword.lower() in lowered:
                return category, rule
    return None, None


def keyword_detect(text: str, update_id: Optional[int] = None) -> Optional[dict]:
    """Single-update keyword detection. Returns a dict or None."""
    category, rule = _match_rule(text)
    if not category:
        return None
    return {
        "risk_detected": True,
        "category": category,
        "title": rule["title"],
        "confidence": 0.66,
        "severity": "MEDIUM",
        "potential_impact": rule["impact"],
        "description": rule["title"],
        "evidence": [text.strip()[:240]],
        "recommended_actions": rule["actions"],
        "time_horizon_days": 60,
        "source_update_ids": [update_id] if update_id is not None else [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def extract_from_updates(updates: List) -> List[dict]:
    """Aggregate keyword detections across an update list.

    Multiple mentions of the same category bump confidence and severity,
    so a pattern is reported rather than a single incident.
    """
    import collections

    now = datetime.now(timezone.utc).isoformat()
    buckets = collections.defaultdict(lambda: {"evidence": [], "ids": [], "count": 0})
    for u in updates:
        category, rule = _match_rule(getattr(u, "content", ""))
        if not category:
            continue
        b = buckets[category]
        b["count"] += 1
        b["evidence"].append(getattr(u, "content", "").strip()[:240])
        b["ids"].append(getattr(u, "id", None))

    results = []
    for category, b in buckets.items():
        count = b["count"]
        confidence = round(min(1.0, 0.6 + count * 0.08), 3)
        severity = "CRITICAL" if count >= 4 else ("HIGH" if count >= 3 else "MEDIUM")
        rule = RULES.get(category, {})
        results.append(
            {
                "risk_detected": True,
                "category": category,
                "title": rule.get("title", category.replace("_", " ").title()),
                "confidence": confidence,
                "severity": severity,
                "potential_impact": rule.get("impact", ["Schedule"]),
                "description": (
                    f"Repeated signals ({count} update(s)) indicate {category.replace('_', ' ').lower()} risk."
                ),
                "evidence": list(dict.fromkeys(b["evidence"]))[:5],
                "recommended_actions": rule.get("actions", ["Review and escalate"]),
                "time_horizon_days": 60,
                "source_update_ids": [i for i in b["ids"] if i is not None],
                "generated_at": now,
            }
        )
    return results


def merge_llm_result(llm: UpdateAnalysisResult, update_id: Optional[int] = None) -> Optional[dict]:
    """Convert a validated LLM result into an EmergingRiskResult shape."""
    if not llm.risk_detected:
        return None
    category = llm.risk_category if llm.risk_category in CATEGORIES else "OTHER"
    return {
        "risk_detected": True,
        "category": category,
        "title": llm.risk_title or "New risk signal",
        "confidence": llm.confidence,
        "severity": llm.severity,
        "potential_impact": [llm.potential_impact] if llm.potential_impact else ["Schedule"],
        "description": f"{category.replace('_', ' ').title()} risk detected from recent updates.",
        "evidence": llm.evidence or [],
        "recommended_actions": llm.recommended_actions,
        "time_horizon_days": llm.time_horizon_days,
        "source_update_ids": [update_id] if update_id is not None else [],
    }


def analyze_update(update_id, update_type, created_at, content) -> dict:
    """Analyze a single update: LLM first, deterministic keywords as fallback.

    Returns a populated EmergingRiskResult-shaped dict (risk_detected may be
    False). Never raises.
    """
    from ai.llm_service import analyze_update as llm_analyze

    llm = llm_analyze(update_id, update_type, created_at, content)
    if llm.risk_detected:
        merged = merge_llm_result(llm, update_id)
        if merged is not None:
            ai_logger.info(
                "emerging risk (llm) update=%s category=%s", update_id, merged["category"]
            )
            return merged

    kw = keyword_detect(content, update_id)
    if kw is not None:
        ai_logger.info(
            "emerging risk (keywords) update=%s category=%s", update_id, kw["category"]
        )
        return kw

    return {
        "risk_detected": False,
        "category": "OTHER",
        "title": "",
        "confidence": 0.5,
        "severity": "MEDIUM",
        "potential_impact": [],
        "description": "",
        "evidence": [],
        "recommended_actions": [],
        "time_horizon_days": None,
        "source_update_ids": [],
    }


__all__ = [
    "CATEGORIES",
    "keyword_detect",
    "extract_from_updates",
    "merge_llm_result",
    "analyze_update",
]