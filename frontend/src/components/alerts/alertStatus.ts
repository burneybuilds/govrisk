import type { Alert } from '../../types';

/**
 * Alert domain helpers shared by `AlertCard` and the Early Warning Center page.
 * Severity and status are unconstrained free text on the server, so every
 * comparison normalises case and tolerates a missing value rather than trusting
 * the wire format.
 */

export function normalizeSeverity(severity: string | undefined | null): string {
  return (severity ?? '').trim().toUpperCase();
}

/**
 * Status is independent of severity: a warning keeps its severity after it is
 * resolved, so severity alone cannot tell a live warning from a closed one.
 */
export function isAlertResolved(alert: Alert): boolean {
  return (alert.status ?? 'ACTIVE').trim().toUpperCase() === 'RESOLVED';
}

/** Higher rank = more urgent. Unrecognised severities sort last. */
const SEVERITY_RANK: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

export const UNKNOWN_SEVERITY_RANK = Object.keys(SEVERITY_RANK).length;

/**
 * Mirror of the server ordering in `routers/alerts.py`: unresolved first, then
 * severity, then most recently detected. Re-applied locally after a status
 * change so acknowledging a warning reorders the list immediately instead of
 * waiting for a refetch.
 */
export function sortAlertsByUrgency(alerts: Alert[]): Alert[] {
  return [...alerts].sort((a, b) => {
    const resolvedA = isAlertResolved(a);
    const resolvedB = isAlertResolved(b);
    if (resolvedA !== resolvedB) return resolvedA ? 1 : -1;

    const rankA = SEVERITY_RANK[normalizeSeverity(a.severity)] ?? UNKNOWN_SEVERITY_RANK;
    const rankB = SEVERITY_RANK[normalizeSeverity(b.severity)] ?? UNKNOWN_SEVERITY_RANK;
    if (rankA !== rankB) return rankA - rankB;

    return (b.detectedDate ?? '').localeCompare(a.detectedDate ?? '');
  });
}
