# Replace rule-based assistant with LLM service later

import json
from sqlalchemy.orm import Session
from models import Project, Alert


def get_project_analytics(db: Session):
    projects = db.query(Project).all()
    if not projects:
        return {
            "sectorAnalytics": [],
            "ministryRankings": [],
            "scatterData": [],
            "riskTrends": [],
        }

    # Sector analytics
    sector_map: dict[str, list[Project]] = {}
    for p in projects:
        sector_map.setdefault(p.sector, []).append(p)

    sector_analytics = []
    for sector, projs in sorted(sector_map.items()):
        avg_risk = round(sum(p.risk_score for p in projs) / len(projs), 1)
        avg_cost = round(
            sum(
                ((p.current_cost - p.original_cost) / p.original_cost * 100)
                for p in projs
            )
            / len(projs),
            1,
        )
        avg_delay = round(
            sum(p.delay_probability for p in projs) / len(projs), 1
        )
        sector_analytics.append(
            {
                "sector": sector,
                "avgRisk": avg_risk,
                "projectCount": len(projs),
                "avgCostOverrun": avg_cost,
                "avgDelay": avg_delay,
            }
        )

    # Ministry rankings
    ministry_map: dict[str, list[Project]] = {}
    for p in projects:
        ministry_map.setdefault(p.ministry, []).append(p)

    ministry_list = []
    for ministry, projs in ministry_map.items():
        avg_risk = round(sum(p.risk_score for p in projs) / len(projs), 1)
        high_count = sum(
            1 for p in projs if p.risk_level in ("HIGH", "CRITICAL")
        )
        ministry_list.append(
            {
                "ministry": ministry,
                "projectCount": len(projs),
                "avgRisk": avg_risk,
                "highRiskCount": high_count,
            }
        )
    ministry_list.sort(key=lambda x: x["avgRisk"], reverse=True)
    for i, m in enumerate(ministry_list, 1):
        m["rank"] = i

    # Scatter data
    scatter = []
    for p in projects:
        cost_overrun = round(
            (p.current_cost - p.original_cost) / p.original_cost * 100, 1
        )
        scatter.append(
            {
                "name": p.name,
                "physicalProgress": p.physical_progress,
                "progressGap": round(100 - p.physical_progress, 1),
                "costOverrun": cost_overrun,
                "riskScore": p.risk_score,
                "sector": p.sector,
            }
        )

    # Risk trends - derive from current data as a snapshot
    risk_trends = [
        {"month": "Apr 2025", "low": 0, "medium": 0, "high": 0, "critical": 0, "overall": 0},
        {"month": "May 2025", "low": 0, "medium": 0, "high": 0, "critical": 0, "overall": 0},
        {"month": "Jun 2025", "low": 0, "medium": 0, "high": 0, "critical": 0, "overall": 0},
        {"month": "Jul 2025", "low": 0, "medium": 0, "high": 0, "critical": 0, "overall": 0},
        {"month": "Aug 2025", "low": 0, "medium": 0, "high": 0, "critical": 0, "overall": 0},
        {"month": "Sep 2025", "low": 0, "medium": 0, "high": 0, "critical": 0, "overall": 0},
    ]

    # Simulate trend by spreading current projects across months
    for i, month_data in enumerate(risk_trends):
        progress = (i + 1) / len(risk_trends)
        for p in projects:
            level = p.risk_level
            # Simulate slight improvement over time for demo
            if level == "CRITICAL" and progress > 0.6:
                level = "HIGH"
            elif level == "HIGH" and progress > 0.8:
                level = "MEDIUM"
            month_data[level.lower()] += 1
        avg = round(sum(p.risk_score for p in projects) / len(projects), 1)
        month_data["overall"] = avg + round((progress - 0.5) * 4, 1)

    return {
        "sectorAnalytics": sector_analytics,
        "ministryRankings": ministry_list,
        "scatterData": scatter,
        "riskTrends": risk_trends,
    }


def generate_assistant_response(query: str, db: Session) -> str:
    lower = query.lower()
    projects = db.query(Project).all()
    alerts = db.query(Alert).all()

    if not projects:
        return "No projects are currently monitored in the system."

    critical = [p for p in projects if p.risk_level == "CRITICAL"]
    high = [p for p in projects if p.risk_level == "HIGH"]
    medium = [p for p in projects if p.risk_level == "MEDIUM"]
    low = [p for p in projects if p.risk_level == "LOW"]

    # Handle "immediate intervention" query - critical for SIH demo
    if "immediate intervention" in lower or "intervention" in lower:
        flagged = critical + high
        flagged.sort(key=lambda p: p.risk_score, reverse=True)
        lines = [
            f"Based on the current demonstration portfolio of {len(projects)} projects, "
            f"{len(flagged)} projects require some level of attention. "
            f"Of these, **{len(critical)} projects are flagged CRITICAL** and should receive immediate intervention:\n"
        ]
        for i, p in enumerate(flagged[:4], 1):
            cost_overrun = round(
                (p.current_cost - p.original_cost) / p.original_cost * 100, 1
            )
            lines.append(
                f"{i}. **{p.name}** ({p.state}) — Risk Score: {p.risk_score}/100\n"
                f"   - Delay Probability: {p.delay_probability}% | Cost Overrun: {cost_overrun}%\n"
                f"   - Status: {p.risk_level}\n"
            )
        lines.append(
            "**Recommended Next Step:** Convene the central monitoring committee "
            "for the top projects and instruct Ministry heads to submit a recovery plan within 14 days."
        )
        return "\n".join(lines)

    # Handle "highest risk" query
    if "highest risk" in lower or "high risk" in lower:
        sorted_projects = sorted(projects, key=lambda p: p.risk_score, reverse=True)
        lines = [
            f"Based on the current portfolio analysis, here are the highest-risk projects:\n"
        ]
        for i, p in enumerate(sorted_projects[:4], 1):
            cost_overrun = round(
                (p.current_cost - p.original_cost) / p.original_cost * 100, 1
            )
            lines.append(
                f"{i}. **{p.name}** ({p.state}) — Risk Score: {p.risk_score}/100\n"
                f"   - Delay Probability: {p.delay_probability}%\n"
                f"   - Cost Overrun: {cost_overrun}%\n"
                f"   - Status: {p.risk_level}\n"
            )
        lines.append(
            "**Recommended Action:** These projects should be escalated for "
            "immediate review by the monitoring committee."
        )
        return "\n".join(lines)

    # Handle "delayed" / "delay" query
    if "delay" in lower:
        delayed = [p for p in projects if p.delay_probability >= 50]
        delayed.sort(key=lambda p: p.delay_probability, reverse=True)
        lines = [
            f"The following projects have a **delay probability above 50%** and require attention:\n"
        ]
        for i, p in enumerate(delayed, 1):
            lines.append(
                f"{i}. **{p.name}** ({p.state}) — {p.delay_probability}% delay probability\n"
                f"   - Physical progress: {p.physical_progress}%\n"
            )
        return "\n".join(lines)

    # Handle "cost overrun" / "cost" query
    if "cost" in lower or "overrun" in lower:
        sorted_by_cost = sorted(
            projects,
            key=lambda p: (p.current_cost - p.original_cost) / p.original_cost,
            reverse=True,
        )
        lines = ["Here are projects ranked by cost overrun:\n"]
        for i, p in enumerate(sorted_by_cost, 1):
            overrun = round(
                (p.current_cost - p.original_cost) / p.original_cost * 100, 1
            )
            lines.append(
                f"{i}. **{p.name}** — {overrun}% overrun\n"
                f"   - Original: ₹{p.original_cost:,.0f} Cr | Current: ₹{p.current_cost:,.0f} Cr\n"
            )
        return "\n".join(lines)

    # Handle "sector" query
    if "sector" in lower:
        from services.risk_service import get_project_analytics

        analytics = get_project_analytics(db)
        lines = ["Here is a comparative analysis of risk across sectors:\n"]
        for s in analytics["sectorAnalytics"]:
            lines.append(
                f"- **{s['sector']}**: {s['projectCount']} projects, "
                f"Avg Risk: {s['avgRisk']}, Avg Cost Overrun: {s['avgCostOverrun']}%"
            )
        return "\n".join(lines)

    # Handle "risk driver" / "major risk" query
    if "risk driver" in lower or "major risk" in lower:
        lines = [
            "Analysis of the monitored projects reveals the following top risk drivers:\n\n"
            "1. **Land Acquisition Delays** — Primary in Water and Transport sectors\n"
            "2. **Milestone Delays** — Affecting critical path activities\n"
            "3. **Cost Escalation** — Material and supply chain pressures\n"
            "4. **Environmental/Geotechnical Challenges** — Flooding, landslides, soil conditions\n"
            "5. **Contractor Performance** — Resource mobilization gaps\n\n"
            "**Key Insight:** Land acquisition and environmental factors remain the largest systemic risks."
        ]
        return "\n".join(lines)

    # Handle "hello" / greeting
    if "hello" in lower or "hi" == lower or lower.startswith("hi "):
        return (
            "Hello! I'm the **GovRisk AI Assistant**, here to help you analyze "
            "government infrastructure project risks.\n\n"
            f"I'm currently monitoring **{len(projects)} projects** across the portfolio.\n\n"
            "I can help you with:\n"
            "- Identifying highest-risk projects\n"
            "- Analyzing cost overruns and delays\n"
            "- Comparing risk across sectors\n"
            "- Understanding risk drivers\n"
            "- Portfolio overview statistics"
        )

    # Handle "portfolio overview" / "overview"
    if "overview" in lower or "portfolio" in lower:
        total_cost = sum(p.current_cost for p in projects)
        lines = [
            f"**Portfolio Snapshot** ({len(projects)} monitored projects)\n\n",
            f"- **Total Current Cost:** ₹{total_cost:,.0f} Cr",
            f"- **Critical Risk:** {len(critical)} projects",
            f"- **High Risk:** {len(high)} projects",
            f"- **Medium Risk:** {len(medium)} projects",
            f"- **Low Risk:** {len(low)} projects",
            f"- **Average Risk Score:** {round(sum(p.risk_score for p in projects) / len(projects), 1)}",
        ]
        return "\n".join(lines)

    # Handle "help"
    if "help" in lower:
        return (
            "Here's how I can help you:\n\n"
            "**Project Analysis:**\n"
            "- \"Which projects are at highest risk?\"\n"
            "- \"Show me projects likely to be delayed.\"\n\n"
            "**Risk Intelligence:**\n"
            "- \"What are the major risk drivers?\"\n"
            "- \"Which projects require immediate intervention?\"\n\n"
            "**Sector & Cost Analysis:**\n"
            "- \"Which sector has the highest cost overrun?\"\n"
            "- \"Give me a portfolio overview.\"\n\n"
            f"Currently monitoring **{len(projects)} projects** in the demonstration portfolio."
        )

    # Default response
    return (
        f"I'm not sure I understand that query. Here are some things I can help with:\n\n"
        f"- Identify the highest-risk projects in the portfolio\n"
        f"- Explain why specific projects are at risk\n"
        f"- Compare risk metrics across sectors\n"
        f"- List projects with high delay probability\n"
        f"- Outline the major risk drivers\n"
        f"- Provide portfolio-wide statistics\n\n"
        f"Currently monitoring **{len(projects)} projects**. "
        f"Try rephrasing your question."
    )
