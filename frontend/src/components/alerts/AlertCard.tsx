import { useState } from 'react';
import { ArrowRight, CheckCircle2, RotateCcw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useI18n } from '../../i18n';
import { useAuth } from '../../context/AuthContext';
import { updateAlertStatus } from '../../services/api';
import { normalizeSeverity, isAlertResolved } from './alertStatus';
import type { Alert, AlertStatus } from '../../types';

interface SeverityStyle {
  border: string;
  badge: string;
  dot: string;
}

const severityConfig: Record<string, SeverityStyle> = {
  CRITICAL: {
    border: 'border-l-red-500',
    badge: 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-100',
    dot: 'bg-red-500',
  },
  HIGH: {
    border: 'border-l-orange-500',
    badge: 'bg-orange-50 text-orange-700 ring-1 ring-inset ring-orange-100',
    dot: 'bg-orange-500',
  },
  MEDIUM: {
    border: 'border-l-yellow-500',
    badge: 'bg-yellow-50 text-yellow-700 ring-1 ring-inset ring-yellow-100',
    dot: 'bg-yellow-500',
  },
  LOW: {
    border: 'border-l-sky-500',
    badge: 'bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-100',
    dot: 'bg-sky-500',
  },
  RESOLVED: {
    border: 'border-l-green-500',
    badge: 'bg-green-50 text-green-700 ring-1 ring-inset ring-green-100',
    dot: 'bg-green-500',
  },
};

// `Alert.severity` is unconstrained free text on the server, so an unexpected
// value must not index into undefined - there is no error boundary above this,
// so a throw here blanks the whole app.
const FALLBACK_SEVERITY: SeverityStyle = {
  border: 'border-l-gray-400',
  badge: 'bg-gray-50 text-gray-700 ring-1 ring-inset ring-gray-100',
  dot: 'bg-gray-400',
};

interface AlertCardProps {
  alert: Alert;
  onStatusChange?: (alert: Alert, status: AlertStatus) => void;
  onError?: (message: string) => void;
}

export function AlertCard({ alert, onStatusChange, onError }: AlertCardProps) {
  const navigate = useNavigate();
  const { sevLabel, t } = useI18n();
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);

  const resolved = isAlertResolved(alert);
  const config = severityConfig[normalizeSeverity(alert.severity)] ?? FALLBACK_SEVERITY;

  // Mirrors the server guard on PATCH /api/alerts/{id} (admin, officer). Hiding
  // the control is a courtesy, not the enforcement point.
  const canUpdate = user?.role === 'admin' || user?.role === 'officer';

  const goToProject = () => {
    navigate(`/projects/${alert.projectId}`);
  };

  const toggleStatus = async () => {
    const next: AlertStatus = resolved ? 'ACTIVE' : 'RESOLVED';
    setBusy(true);
    try {
      const updated = await updateAlertStatus(alert.id, next);
      onStatusChange?.(updated, next);
    } catch (err) {
      onError?.(err instanceof Error ? err.message : t('alertCard.statusFailed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className={`rounded-xl border border-gray-200 border-l-4 bg-white p-5 transition-shadow hover:shadow-sm ${
        config.border
      } ${resolved ? 'opacity-70' : ''}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${config.dot}`} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${config.badge}`}
              >
                {sevLabel(alert.severity)}
              </span>
              <span className="text-sm font-semibold text-navy-900">{alert.type}</span>
              {/* An alert keeps its severity once resolved, so without an
                  explicit status marker a resolved CRITICAL warning still reads
                  as a live red alert on the "All" tab. */}
              {resolved && (
                <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-[11px] font-semibold text-green-700 ring-1 ring-inset ring-green-100">
                  <CheckCircle2 className="h-3 w-3" />
                  {t('alertCard.resolved')}
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={goToProject}
              className="mt-1 text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline"
            >
              {alert.projectName}
            </button>
          </div>
        </div>
        <span className="shrink-0 text-xs text-gray-400">{alert.detectedDate}</span>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-gray-600">{alert.description}</p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={goToProject}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-navy-900 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
        >
          {t('alertCard.viewProject')}
          <ArrowRight className="h-3.5 w-3.5" />
        </button>

        {canUpdate && (
          <button
            type="button"
            onClick={toggleStatus}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-navy-900 transition-colors hover:border-green-200 hover:bg-green-50 hover:text-green-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {resolved ? (
              <>
                <RotateCcw className="h-3.5 w-3.5" />
                {t('alertCard.reopen')}
              </>
            ) : (
              <>
                <CheckCircle2 className="h-3.5 w-3.5" />
                {t('alertCard.resolve')}
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
