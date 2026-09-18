"""Normalization helpers shared by every ingestion adapter.

These functions map provider-specific vocabulary onto the platform's single
canonical vocabulary (sectors, scale thresholds, state names) so database rows
and map joins are consistent regardless of which source produced them.
"""

from __future__ import annotations

from typing import Optional

from .contract import ProjectScale

# --- Sectors ------------------------------------------------------------------
# Canonical sectors mirror the platform schema (see backend/schemas.py
# VALID_SECTORS) plus "Other" as the safety net for unmapped values.

CANONICAL_SECTORS = {
    "Roads": "Transport",
    "Transport": "Transport",
    "Highways": "Transport",
    "Road": "Transport",
    "Road Transport": "Transport",
    "Railways": "Transport",
    "Railways & Metro": "Transport",
    "Rail": "Transport",
    "Metro": "Transport",
    "Urban Transit": "Transport",
    "Transit": "Transport",
    "Airports": "Transport",
    "Airport": "Transport",
    "Ports": "Transport",
    "Port": "Transport",
    "Shipping": "Transport",
    "Power": "Energy",
    "Energy": "Energy",
    "Electricity": "Energy",
    "Transmission": "Energy",
    "Distribution": "Energy",
    "Renewable Energy": "Energy",
    "Solar": "Energy",
    "Wind": "Energy",
    "Hydro": "Energy",
    "Thermal": "Energy",
    "Nuclear": "Energy",
    "Oil & Gas": "Energy",
    "Petroleum": "Energy",
    "Water": "Water",
    "Irrigation": "Water",
    "Water Supply": "Water",
    "Drinking Water": "Water",
    "Flood Control": "Water",
    "Drainage": "Water",
    "Communication": "Communication",
    "Telecom": "Communication",
    "Telecommunications": "Communication",
    "Digital": "Communication",
    "IT": "Communication",
    "Social Infrastructure": "Social Infrastructure",
    "Housing": "Social Infrastructure",
    "Urban Housing": "Social Infrastructure",
    "Health": "Social Infrastructure",
    "Hospitals": "Social Infrastructure",
    "Education": "Social Infrastructure",
    "Schools": "Social Infrastructure",
    "Colleges": "Social Infrastructure",
    "Mining": "Mining",
    "Minerals": "Mining",
    "Coal": "Mining",
}


def canonical_sector(raw: Optional[str]) -> str:
    """Map a source sector label onto the canonical set (case-insensitive)."""
    if not raw:
        return "Other"
    key = " ".join(str(raw).strip().split())
    direct = CANONICAL_SECTORS.get(key.title()) or CANONICAL_SECTORS.get(key)
    if direct:
        return direct
    lowered = key.lower()
    for label, target in CANONICAL_SECTORS.items():
        if label.lower() in lowered:
            return target
    return "Other"


# --- Scale thresholds ----------------------------------------------------------
MEDIUM_MIN_CR = 100.0
LARGE_MIN_CR = 1000.0


def derive_scale(cost_estimate_cr: Optional[float]) -> Optional[ProjectScale]:
    """MEDIUM = 100-1000 Cr, LARGE > 1000 Cr. None when cost unknown."""
    if cost_estimate_cr is None:
        return None
    if cost_estimate_cr > LARGE_MIN_CR:
        return ProjectScale.LARGE
    if cost_estimate_cr >= MEDIUM_MIN_CR:
        return ProjectScale.MEDIUM
    return None


# --- State name aliases --------------------------------------------------------
# GADM / data.gov.in name variants normalised to the canonical name used by the
# map boundary join (mirrors frontend `utils/geo.ts` resolveStateKey).

STATE_ALIASES = {
    "Orissa": "Odisha",
    "Odisha": "Odisha",
    "Uttaranchal": "Uttarakhand",
    "Uttarakhand": "Uttarakhand",
    "Andaman & Nicobar Islands": "Andaman and Nicobar Islands",
    "Andaman and Nicobar Islands": "Andaman and Nicobar Islands",
    "Dadra & Nagar Haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu",
    "Dadra and Nagar Haveli and Daman and Diu": "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi": "Delhi",
    "National Capital Territory of Delhi": "Delhi",
    "NCT Of Delhi": "Delhi",
    "Puducherry": "Puducherry",
    "Pondicherry": "Puducherry",
    "Chhattisgarh": "Chhattisgarh",
    "Jammu and Kashmir": "Jammu and Kashmir",
    "Jammu & Kashmir": "Jammu and Kashmir",
    "Ladakh": "Ladakh",
    "Telangana": "Telangana",
    "Andhra Pradesh": "Andhra Pradesh",
    "Arunachal Pradesh": "Arunachal Pradesh",
    "Assam": "Assam",
    "Bihar": "Bihar",
    "Goa": "Goa",
    "Gujarat": "Gujarat",
    "Haryana": "Haryana",
    "Himachal Pradesh": "Himachal Pradesh",
    "Jharkhand": "Jharkhand",
    "Karnataka": "Karnataka",
    "Kerala": "Kerala",
    "Madhya Pradesh": "Madhya Pradesh",
    "Maharashtra": "Maharashtra",
    "Manipur": "Manipur",
    "Meghalaya": "Meghalaya",
    "Mizoram": "Mizoram",
    "Nagaland": "Nagaland",
    "Punjab": "Punjab",
    "Rajasthan": "Rajasthan",
    "Sikkim": "Sikkim",
    "Tamil Nadu": "Tamil Nadu",
    "Tripura": "Tripura",
    "Uttar Pradesh": "Uttar Pradesh",
    "West Bengal": "West Bengal",
}


def canonical_state(raw: Optional[str]) -> str:
    """Canonical state name for consistent DB rows and map geometry joins."""
    if not raw:
        return "Unknown"
    key = " ".join(str(raw).strip().split())
    return STATE_ALIASES.get(key, key)


def to_iso_date(value: Optional[str]) -> Optional[str]:
    """Coerce common date spellings to YYYY-MM-DD (or None when unparsable)."""
    if not value:
        return None
    from datetime import datetime

    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


__all__ = [
    "canonical_sector",
    "canonical_state",
    "derive_scale",
    "to_iso_date",
    "MEDIUM_MIN_CR",
    "LARGE_MIN_CR",
    "CANONICAL_SECTORS",
    "STATE_ALIASES",
]