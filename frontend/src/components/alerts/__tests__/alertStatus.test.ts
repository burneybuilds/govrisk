import { describe, it, expect } from 'vitest';
import {
  normalizeSeverity,
  isAlertResolved,
  sortAlertsByUrgency,
  UNKNOWN_SEVERITY_RANK,
} from '../alertStatus';
import type { Alert, AlertStatus } from '../../../types';

function makeAlert(partial: Partial<Alert> & { id: string }): Alert {
  return {
    projectId: 'PRJ-001',
    projectName: 'Test Project',
    type: 'Test Alert',
    severity: 'MEDIUM',
    status: 'ACTIVE',
    detectedDate: '2025-01-01',
    description: 'desc',
    ...partial,
  };
}

const ids = (alerts: Alert[]) => alerts.map((a) => a.id);

describe('normalizeSeverity', () => {
  it('upper-cases and trims free-text severity from the server', () => {
    expect(normalizeSeverity('critical')).toBe('CRITICAL');
    expect(normalizeSeverity('  High  ')).toBe('HIGH');
  });

  it('tolerates missing values instead of throwing', () => {
    expect(normalizeSeverity(undefined)).toBe('');
    expect(normalizeSeverity(null)).toBe('');
  });
});

describe('isAlertResolved', () => {
  it('defaults a missing status to active', () => {
    expect(isAlertResolved(makeAlert({ id: 'A', status: undefined }))).toBe(false);
  });

  it('is case-insensitive and trims', () => {
    // Cast: the point is that the runtime helper tolerates unvalidated server
    // input even though the TypeScript type is strict.
    expect(
      isAlertResolved(makeAlert({ id: 'A', status: ' resolved ' as AlertStatus }))
    ).toBe(true);
  });

  it('does not infer resolution from severity', () => {
    // A CRITICAL warning that has been closed is still CRITICAL; conflating the
    // two is what previously misfiled every resolved alert.
    expect(isAlertResolved(makeAlert({ id: 'A', severity: 'CRITICAL', status: 'RESOLVED' }))).toBe(
      true
    );
    expect(isAlertResolved(makeAlert({ id: 'A', severity: 'CRITICAL', status: 'ACTIVE' }))).toBe(
      false
    );
  });
});

describe('sortAlertsByUrgency', () => {
  it('puts unresolved warnings above resolved ones regardless of severity', () => {
    const sorted = sortAlertsByUrgency([
      makeAlert({ id: 'resolved-critical', severity: 'CRITICAL', status: 'RESOLVED' }),
      makeAlert({ id: 'active-low', severity: 'LOW', status: 'ACTIVE' }),
    ]);
    expect(ids(sorted)).toEqual(['active-low', 'resolved-critical']);
  });

  it('orders by severity, then newest first within a severity', () => {
    const sorted = sortAlertsByUrgency([
      makeAlert({ id: 'med-old', severity: 'MEDIUM', detectedDate: '2025-01-01' }),
      makeAlert({ id: 'crit-old', severity: 'CRITICAL', detectedDate: '2025-01-01' }),
      makeAlert({ id: 'crit-new', severity: 'CRITICAL', detectedDate: '2025-09-01' }),
      makeAlert({ id: 'high', severity: 'HIGH', detectedDate: '2025-05-01' }),
    ]);
    expect(ids(sorted)).toEqual(['crit-new', 'crit-old', 'high', 'med-old']);
  });

  it('sorts an unrecognised severity last instead of first', () => {
    const sorted = sortAlertsByUrgency([
      makeAlert({ id: 'weird', severity: 'catastrophic' as Alert['severity'] }),
      makeAlert({ id: 'low', severity: 'LOW' }),
    ]);
    expect(ids(sorted)).toEqual(['low', 'weird']);
    expect(UNKNOWN_SEVERITY_RANK).toBeGreaterThan(3);
  });

  it('matches on severity case-insensitively', () => {
    const sorted = sortAlertsByUrgency([
      makeAlert({ id: 'mixed', severity: 'critical' as Alert['severity'] }),
      makeAlert({ id: 'upper', severity: 'MEDIUM' }),
    ]);
    expect(ids(sorted)).toEqual(['mixed', 'upper']);
  });

  it('does not mutate the input array', () => {
    const input = [
      makeAlert({ id: 'b', severity: 'HIGH' }),
      makeAlert({ id: 'a', severity: 'CRITICAL' }),
    ];
    const copy = [...input];
    sortAlertsByUrgency(input);
    expect(input).toEqual(copy);
  });
});
