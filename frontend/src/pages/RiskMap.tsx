import { useMemo, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';
import { MapIcon, Table2 } from 'lucide-react';
import { MapContainer, DataTableFallback } from '../components/map';
import { useRegionRiskData } from '../hooks/useRegionRiskData';
import { useRiskScores } from '../hooks/useRiskScores';
import { useMapLayerState } from '../hooks/useMapLayerState';
import { useI18n } from '../i18n';
import type { StateKey } from '../types/map';

type ViewMode = 'map' | 'table';

function useViewMode(): [ViewMode, (mode: ViewMode) => void] {
  const location = useLocation();
  const navigate = useNavigate();
  const mode: ViewMode =
    new URLSearchParams(location.search).get('view') === 'table' ? 'table' : 'map';
  const setMode = useCallback(
    (next: ViewMode) => {
      navigate(next === 'table' ? '?view=table' : '?view=map', { replace: true });
    },
    [navigate],
  );
  return [mode, setMode];
}

export default function RiskMap() {
  const [mode, setMode] = useViewMode();
  const { regions, isInitialLoading, status } = useRegionRiskData();
  const riskScores = useRiskScores();
  const layerControls = useMapLayerState();
  const { t } = useI18n();

  const summary = useMemo(() => {
    if (regions.length === 0) return null;
    const totalProjects = regions.reduce((sum, r) => sum + r.projectCount, 0);
    const weighted = regions.reduce((sum, r) => sum + r.compositeScore * r.projectCount, 0);
    const highRegions = regions.filter(
      (r) => r.riskLevel === 'HIGH' || r.riskLevel === 'CRITICAL',
    ).length;
    return {
      totalProjects,
      avgScore: totalProjects > 0 ? weighted / totalProjects : 0,
      highRegions,
    };
  }, [regions]);

  const handleSelectRegion = useCallback((_key: StateKey, _stateName: string) => {}, []);

  return (
    <div className="mx-auto min-w-0 max-w-[1400px] px-4 pb-8 pt-6 lg:px-6">
      <header className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">
            {t('riskMap.title')}
          </h1>
          <p className="mt-1 text-sm text-gray-500 lg:text-base">{t('riskMap.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          {summary && (
            <div className="hidden items-center gap-4 rounded-lg border border-gray-200 bg-white px-4 py-2 text-[13px] text-gray-600 sm:flex">
              <span>
                <b className="tabular-nums text-navy-900">{summary.totalProjects}</b>{' '}
                {t('riskMap.summaryProjects', { count: summary.totalProjects }).replace(
                  `${summary.totalProjects} `,
                  '',
                )}
              </span>
              <span className="h-4 w-px bg-gray-200" />
              <span>
                {t('riskMap.avgComposite', { score: summary.avgScore.toFixed(0) })
                  .replace(`${summary.avgScore.toFixed(0)}`, '')
                  .trim()}{' '}
                <b className="tabular-nums text-navy-900">{summary.avgScore.toFixed(0)}</b>
              </span>
              <span className="h-4 w-px bg-gray-200" />
              <span>
                <b className="tabular-nums text-red-600">{summary.highRegions}</b>{' '}
                {t('riskMap.highRegions', { count: summary.highRegions }).replace(
                  `${summary.highRegions} `,
                  '',
                )}
              </span>
            </div>
          )}
          <div
            role="tablist"
            aria-label={t('riskMap.mapViewAria')}
            className="flex rounded-lg border border-gray-300 bg-white p-0.5 text-sm"
          >
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'map'}
              onClick={() => setMode('map')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors ${
                mode === 'map' ? 'bg-navy-900 text-white' : 'text-gray-500 hover:text-navy-900'
              }`}
            >
              <MapIcon size={14} />
              <span>{t('riskMap.mapToggle')}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'table'}
              onClick={() => setMode('table')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors ${
                mode === 'table' ? 'bg-navy-900 text-white' : 'text-gray-500 hover:text-navy-900'
              }`}
            >
              <Table2 size={14} />
              <span>{t('riskMap.tableToggle')}</span>
            </button>
          </div>
        </div>
      </header>

      {mode === 'map' ? (
        <div className="h-[calc(100vh-180px)] min-h-[560px] overflow-hidden rounded-xl border border-gray-300 shadow-sm">
          <MapContainer
            regions={regions}
            points={riskScores.data?.points ?? []}
            factorDrivers={riskScores.data?.factorDrivers ?? []}
            dataStatus={status}
            isInitialLoading={isInitialLoading}
            layerState={layerControls.state}
            layerControls={layerControls}
            onSelectRegion={handleSelectRegion}
          />
        </div>
      ) : (
        <DataTableFallback
          regions={regions}
          onSelectRegion={handleSelectRegion}
          isLoading={isInitialLoading}
        />
      )}

      <div className="sr-only" aria-live="polite">
        {isInitialLoading ? t('riskMap.loadingIntelligence') : t('riskMap.updated')}
      </div>
    </div>
  );
}
