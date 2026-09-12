import { memo, useMemo } from 'react';
import type {
  DisasterSummary,
  FactorDriver,
  ProjectRiskPoint,
  RegionRiskData,
  SelectedRegion,
  StateKey,
  WeatherSummary,
} from '../../types/map';
import { levelForScore, resolveStateKey } from '../../constants/regions';
import { Skeleton } from './Skeleton';
import { RegionList } from './RegionList';

export interface RegionDetailPanelProps {
  selected: SelectedRegion | null;
  regions: readonly RegionRiskData[];
  factorDrivers: readonly FactorDriver[];
  points: readonly ProjectRiskPoint[];
  status: {
    risk: { isLoading: boolean };
    disaster: { isLoading: boolean };
    weather: { isLoading: boolean };
  };
  onClose: () => void;
  onSelectRegion: (key: StateKey | null) => void;
  onSelectProject: (point: ProjectRiskPoint) => void;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded bg-white/5 px-2 py-2 text-center">
      <div className="text-lg font-semibold tabular-nums text-gray-100">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-gray-500">{label}</div>
    </div>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
      {children}
    </h3>
  );
}

function FactorBars({ factors }: { factors: readonly FactorDriver[] }) {
  const max = useMemo(() => Math.max(1, ...factors.map((f) => f.avgScore)), [factors]);
  return (
    <ul className="space-y-1.5">
      {factors.map((f) => {
        const width = Math.round((f.avgScore / max) * 100);
        return (
          <li key={f.key}>
            <div className="flex justify-between text-[12px] text-gray-300">
              <span className="truncate pr-2">{f.name}</span>
              <span className="tabular-nums text-gray-400">{f.avgScore.toFixed(0)}</span>
            </div>
            <div
              role="progressbar"
              aria-valuenow={width}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={f.name}
              className="h-1.5 w-full overflow-hidden rounded-full bg-white/10"
            >
              <div
                className="h-full rounded-full bg-gradient-to-r from-purple-500 to-amber-400"
                style={{ width: `${width}%` }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function DisasterSummaryBlock({
  summary,
  loading,
}: {
  summary: DisasterSummary | undefined;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
  }
  if (!summary || !summary.regionAvailable || summary.totalEvents === 0) {
    return (
      <p className="text-[12px] text-gray-400">No disaster history recorded for this region.</p>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-2 text-[12px]">
      <div className="rounded bg-white/5 px-2 py-1.5">
        <div className="text-gray-400">Total events</div>
        <div className="text-lg font-semibold tabular-nums text-amber-300">
          {summary.totalEvents}
        </div>
      </div>
      <div className="rounded bg-white/5 px-2 py-1.5">
        <div className="text-gray-400">Dominant hazard</div>
        <div className="truncate font-semibold text-gray-100">{summary.dominantType ?? '—'}</div>
      </div>
      {summary.lastEventYear != null && (
        <p className="col-span-2 text-[11px] text-gray-500">
          Most recent event: {summary.lastEventYear}
        </p>
      )}
    </div>
  );
}

function WeatherSummaryBlock({
  weather,
  loading,
}: {
  weather: WeatherSummary | undefined;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
  }
  if (!weather || !weather.regionAvailable) {
    return <p className="text-[12px] text-gray-400">No live weather snapshot available.</p>;
  }
  return (
    <div className="space-y-1.5 text-[12px]">
      <div className="flex justify-between rounded bg-white/5 px-2 py-1.5">
        <span className="text-gray-400">Condition</span>
        <span className="font-semibold text-gray-100">{weather.condition}</span>
      </div>
      {weather.activeAlerts.length > 0 && (
        <ul className="space-y-1">
          {weather.activeAlerts.map((a) => (
            <li
              key={a.id}
              className="flex items-start justify-between gap-2 rounded bg-red-500/10 px-2 py-1.5"
            >
              <span className="text-red-200">{a.headline}</span>
              <span className="flex-none text-[10px] font-bold uppercase text-red-300">
                {a.severity}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RegionDetailPanelInner({
  selected,
  regions,
  factorDrivers,
  points,
  status,
  onClose,
  onSelectRegion,
  onSelectProject,
}: RegionDetailPanelProps) {
  const region = useMemo(
    () => (selected ? (regions.find((r) => r.stateKey === selected.stateKey) ?? null) : null),
    [selected, regions],
  );

  const regionProjects = useMemo(
    () =>
      selected
        ? points
            .filter((p) => resolveStateKey(p.stateName) === selected.stateKey)
            .sort((a, b) => b.riskScore - a.riskScore)
            .slice(0, 5)
        : [],
    [selected, points],
  );

  const topFactors = useMemo(
    () => factorDrivers.filter((f) => f.avgScore > 0).slice(0, 10),
    [factorDrivers],
  );

  return (
    <aside
      aria-label="Region intelligence"
      className="pointer-events-auto flex w-full max-h-full flex-col overflow-hidden rounded-t-2xl border border-white/10 bg-[#0f1830]/95 text-gray-100 shadow-2xl backdrop-blur md:max-h-[calc(100%-3rem)] md:rounded-l-2xl md:rounded-r-none md:max-w-none"
    >
      <div className="flex items-center justify-between gap-2 border-b border-white/10 px-4 py-3">
        {region ? (
          <>
            <h2 className="truncate text-base font-semibold text-amber-300">{region.stateName}</h2>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-semibold text-gray-200">
                {levelForScore(region.compositeScore)} · {Math.round(region.compositeScore)}/100
              </span>
              <button
                type="button"
                onClick={onClose}
                aria-label={`Close ${region.stateName} details`}
                className="rounded p-1 text-gray-400 hover:bg-white/10 hover:text-gray-100 focus-visible:outline-2 focus-visible:outline-amber-400"
              >
                ✕
              </button>
            </div>
          </>
        ) : (
          <>
            <h2 className="text-base font-semibold text-gray-200">All regions</h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close panel"
              className="rounded p-1 text-gray-400 hover:bg-white/10 hover:text-gray-100 focus-visible:outline-2 focus-visible:outline-amber-400 md:hidden"
            >
              ✕
            </button>
          </>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {region ? (
          <div className="space-y-5">
            <section>
              <SectionLabel>Project portfolio</SectionLabel>
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Projects" value={String(region.projectCount)} />
                <Stat label="Avg risk" value={region.avgRisk.toFixed(0)} />
                <Stat
                  label="High+/critical"
                  value={String(region.highRiskProjects + region.criticalRiskProjects)}
                />
              </div>
            </section>
            {region.contributingFactors.length > 0 && (
              <section>
                <SectionLabel>Contributing factors</SectionLabel>
                <ul className="flex flex-wrap gap-1.5">
                  {region.contributingFactors.map((f) => (
                    <li
                      key={f}
                      className="rounded-full bg-purple-500/15 px-2.5 py-1 text-[11px] text-purple-200"
                    >
                      {f}
                    </li>
                  ))}
                </ul>
              </section>
            )}
            <section>
              <SectionLabel>Disaster history</SectionLabel>
              <DisasterSummaryBlock summary={region.disaster} loading={status.disaster.isLoading} />
            </section>
            <section>
              <SectionLabel>Live weather</SectionLabel>
              <WeatherSummaryBlock weather={region.weather} loading={status.weather.isLoading} />
            </section>
            <section>
              <SectionLabel>Infrastructure projects</SectionLabel>
              {regionProjects.length > 0 ? (
                <ul className="space-y-1">
                  {regionProjects.map((project) => (
                    <li key={project.id}>
                      <button
                        type="button"
                        onClick={() => onSelectProject(project)}
                        className="flex w-full items-center justify-between gap-2 rounded bg-white/5 px-2.5 py-2 text-left hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-amber-400"
                      >
                        <span className="min-w-0">
                          <span className="block truncate text-[12px] font-medium text-gray-100">
                            {project.name}
                          </span>
                          <span className="block text-[10px] uppercase tracking-wide text-gray-500">
                            {project.status ?? 'ONGOING'} · {project.sector ?? '—'}
                          </span>
                        </span>
                        <span
                          className={`flex-none text-[11px] font-semibold ${
                            project.riskLevel === 'HIGH' || project.riskLevel === 'CRITICAL'
                              ? 'text-amber-300'
                              : 'text-gray-300'
                          }`}
                        >
                          {project.riskScore}/100
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[12px] text-gray-400">No project markers in this region.</p>
              )}
            </section>
          </div>
        ) : (
          <div className="space-y-4">
            {topFactors.length > 0 && (
              <section>
                <SectionLabel>Top risk drivers</SectionLabel>
                <FactorBars factors={topFactors} />
              </section>
            )}
            <section>
              <SectionLabel>Browse regions (by score)</SectionLabel>
              <RegionList
                regions={regions}
                selectedKey={selected?.stateKey}
                onSelect={(key) => onSelectRegion(key)}
                isLoading={status.risk.isLoading}
              />
            </section>
          </div>
        )}
      </div>
    </aside>
  );
}

export const RegionDetailPanel = memo(RegionDetailPanelInner);
