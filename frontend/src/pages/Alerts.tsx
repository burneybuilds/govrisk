import { useState, useEffect, useCallback } from 'react';
import { getAlerts } from '../services/api';
import { AlertCard } from '../components/alerts/AlertCard';
import {
  normalizeSeverity,
  isAlertResolved,
  sortAlertsByUrgency,
} from '../components/alerts/alertStatus';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { BellOff, RefreshCw } from 'lucide-react';
import { useI18n, TranslationKey } from '../i18n';
import type { Alert } from '../types';

const tabs = ['All', 'Critical', 'High', 'Medium', 'Low', 'Resolved'] as const;

type Tab = (typeof tabs)[number];

const tabLabels: Record<Tab, TranslationKey> = {
  All: 'alerts.all',
  Critical: 'alerts.critical',
  High: 'alerts.high',
  Medium: 'alerts.medium',
  Low: 'alerts.low',
  Resolved: 'alerts.resolved',
};

// Severity buckets, highest first. Anything unrecognised falls into the last
// bucket so it stays reachable instead of silently vanishing from every tab.
const SEVERITY_TABS: Record<string, Tab> = {
  CRITICAL: 'Critical',
  HIGH: 'High',
  MEDIUM: 'Medium',
};
const LOW_TAB: Tab = 'Low';

const severityTab = (alert: Alert): Tab => SEVERITY_TABS[normalizeSeverity(alert.severity)] ?? LOW_TAB;

export default function Alerts() {
  const { t } = useI18n();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('All');
  const [requestId, setRequestId] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getAlerts()
      .then((data) => {
        if (!cancelled) setAlerts(sortAlertsByUrgency(data));
      })
      .catch((err) => {
        // Store only the server detail; the heading is rendered from `t` below so
        // it stays in the active language.
        if (!cancelled) setError(err?.message ?? '');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [requestId]);

  // Reset the request state here rather than at the top of the effect so the
  // click gets immediate feedback instead of an extra render pass.
  const retry = useCallback(() => {
    setLoading(true);
    setError(null);
    setRequestId((n) => n + 1);
  }, []);

  const handleStatusChange = useCallback((updated: Alert) => {
    setActionError(null);
    setAlerts((prev) => sortAlertsByUrgency(prev.map((a) => (a.id === updated.id ? updated : a))));
  }, []);

  // Severity and status are different things: an alert keeps its severity
  // after it is resolved. Filtering the "Resolved" tab on severity misfiled
  // every resolved alert that was not itself severity=RESOLVED, so filter on
  // `status` and keep resolved alerts out of the active-severity tabs.
  const active = alerts.filter((a) => !isAlertResolved(a));

  const tabCounts: Record<Tab, number> = {
    All: alerts.length,
    Critical: active.filter((a) => severityTab(a) === 'Critical').length,
    High: active.filter((a) => severityTab(a) === 'High').length,
    Medium: active.filter((a) => severityTab(a) === 'Medium').length,
    Low: active.filter((a) => severityTab(a) === LOW_TAB).length,
    Resolved: alerts.length - active.length,
  };

  const filteredAlerts =
    activeTab === 'All'
      ? alerts
      : activeTab === 'Resolved'
        ? alerts.filter(isAlertResolved)
        : active.filter((alert) => severityTab(alert) === activeTab);

  return (
    <div className="mx-auto min-w-0 max-w-[1100px]">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">
          {t('alerts.title')}
        </h1>
        <p className="mt-1 text-sm text-gray-500 lg:text-base">
          Potential project risks detected by GovRisk
        </p>
      </div>

      {actionError && (
        <div className="mb-4 flex items-start justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          <span>{actionError}</span>
          <button
            type="button"
            onClick={() => setActionError(null)}
            className="shrink-0 font-medium text-amber-900 underline"
          >
            {t('common.close')}
          </button>
        </div>
      )}

      {loading ? (
        <LoadingState text={t('alerts.loading')} />
      ) : error !== null ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <p className="font-semibold">{t('alerts.failed')}</p>
          {error && <p className="mt-1 text-xs">{error}</p>}
          <button
            type="button"
            onClick={retry}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-100"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {t('common.retry')}
          </button>
        </div>
      ) : (
        <>
          <div className="mb-6 flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? 'bg-navy-900 text-white'
                    : 'border border-gray-200 bg-white text-gray-600 hover:border-navy-300 hover:text-navy-900'
                }`}
              >
                {t(tabLabels[tab])}
                <span
                  className={`ml-2 rounded-full px-1.5 text-xs ${activeTab === tab ? 'bg-white/20' : 'bg-gray-100 text-gray-500'}`}
                >
                  {tabCounts[tab]}
                </span>
              </button>
            ))}
          </div>

          <p className="mb-4 text-sm text-gray-500">
            {t('alerts.showing', { count: filteredAlerts.length })}
          </p>

          {filteredAlerts.length === 0 ? (
            <EmptyState
              title={t('alerts.noTitle')}
              description={t('alerts.noDesc')}
              icon={<BellOff size={40} />}
            />
          ) : (
            <div className="space-y-4">
              {filteredAlerts.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onStatusChange={handleStatusChange}
                  onError={setActionError}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
