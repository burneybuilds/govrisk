#!/usr/bin/env python
"""Print the aggregate-fidelity report and exit non-zero on any breach.

Usage: python scripts/run_validate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paimana.data.loader import load_processed_projects  # noqa: E402
from paimana.data.validate import compute_fidelity_report, format_report  # noqa: E402


def main() -> int:
    projects = load_processed_projects()
    checks = compute_fidelity_report(projects)
    print(format_report(checks))
    failures = [c for c in checks if not c.passed]
    if failures:
        print(f"\n{len(failures)} anchor(s) FAILED tolerance band.")
        return 1
    print("\nAll anchors within tolerance.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
