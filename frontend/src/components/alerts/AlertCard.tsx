import { ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useI18n } from '../../i18n';
import type { Alert } from '../../types';

const severityConfig = {
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
  RESOLVED: {
    border: 'border-l-green-500',
    badge: 'bg-green-50 text-green-700 ring-1 ring-inset ring-green-100',
    dot: 'bg-green-500',
  },
};

export function AlertCard({ alert }: { alert: Alert }) {
  const navigate = useNavigate();
  const { sevLabel, t } = useI18n();
  const config = severityConfig[alert.severity];

  const goToProject = () => {
    navigate(`/projects/${alert.projectId}`);
  };

  return (
    <div
      className={`border-l-4 rounded-xl border border-gray-200 bg-white p-5 transition-shadow hover:shadow-sm ${config.border}`}
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

      <div className="mt-4">
        <button
          type="button"
          onClick={goToProject}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-navy-900 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
        >
          {t('alertCard.viewProject')}
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
