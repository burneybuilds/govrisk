import { memo, useMemo, useState } from 'react';
import type { RegionRiskData, StateKey } from '../../types/map';
import { levelForScore } from '../../constants/regions';
import { Skeleton } from './Skeleton';

export type SortKey =
  'name' | 'compositeScore' | 'projectCount' | 'disasterEvents' | 'severeAlerts';

export interface DataTableFallbackProps {
  regions: readonly RegionRiskData[];
  selectedKey?: StateKey | null;
  onSelectRegion: (key: StateKey, stateName: string) => void;
  isLoading?: boolean;
}

const COLUMNS: ReadonlyArray<{ key: SortKey; label: string; numeric?: boolean }> = [
  { key: 'name', label: 'State / UT' },
  { key: 'compositeScore', label: 'Composite risk', numeric: true },
  { key: 'projectCount', label: 'Projects', numeric: true },
  { key: 'disasterEvents', label: 'Disaster events', numeric: true },
  { key: 'severeAlerts', label: 'Severe alerts', numeric: true },
];

function comparator(a: RegionRiskData, b: RegionRiskData, key: SortKey): number {
  switch (key) {
    case 'name':
      return a.stateName.localeCompare(b.stateName);
    case 'compositeScore':
      return a.compositeScore - b.compositeScore;
    case 'projectCount':
      return a.projectCount - b.projectCount;
    case 'disasterEvents':
      return (a.disaster?.totalEvents ?? 0) - (b.disaster?.totalEvents ?? 0);
    case 'severeAlerts':
      return (
        (a.weather?.activeAlerts.filter((al) => al.severity !== 'MODERATE').length ?? 0) -
        (b.weather?.activeAlerts.filter((al) => al.severity !== 'MODERATE').length ?? 0)
      );
  }
}

function DataTableFallbackInner({
  regions,
  selectedKey = null,
  onSelectRegion,
  isLoading = false,
}: DataTableFallbackProps) {
  const [sortKey, setSortKey] = useState<SortKey>('compositeScore');
  const [desc, setDesc] = useState(true);

  const rows = useMemo(() => {
    const sorted = [...regions].sort((a, b) => {
      const cmp = comparator(a, b, sortKey);
      return desc ? -cmp : cmp;
    });
    return sorted;
  }, [regions, sortKey, desc]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setDesc((d) => !d);
    } else {
      setSortKey(key);
      setDesc(key === 'compositeScore');
    }
  };

  return (
    <section
      aria-label="Risk summary table"
      className="overflow-hidden rounded-xl border border-white/10 bg-[#0f1830]/80 shadow-lg backdrop-blur"
    >
      <header className="flex items-center justify-between gap-2 border-b border-white/10 px-4 py-3">
        <h2 className="text-sm font-semibold text-gray-100">Regional risk matrix</h2>
        <p className="text-[11px] text-gray-500">Click a row to focus it on the map</p>
      </header>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-[13px]">
          <caption className="sr-only">
            Risk indicators by state and union territory, sorted by{' '}
            {COLUMNS.find((c) => c.key === sortKey)?.label.toLowerCase()}
            {desc ? ' descending' : ' ascending'}.
          </caption>
          <thead>
            <tr className="border-b border-white/10 text-gray-400">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  aria-sort={sortKey === col.key ? (desc ? 'descending' : 'ascending') : 'none'}
                  className={`px-4 py-2.5 font-medium ${col.numeric ? 'text-right' : ''}`}
                >
                  <button
                    type="button"
                    onClick={() => toggleSort(col.key)}
                    className={sortKey === col.key ? 'text-amber-300' : 'hover:text-gray-200'}
                  >
                    {col.label}
                    {sortKey === col.key ? (desc ? ' ↓' : ' ↑') : ''}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 6 }, (_, i) => (
                  <tr key={i} className="border-b border-white/5">
                    {COLUMNS.map((col) => (
                      <td key={col.key} className={`px-4 py-3 ${col.numeric ? 'text-right' : ''}`}>
                        <Skeleton className="h-3.5 w-16" />
                      </td>
                    ))}
                  </tr>
                ))
              : rows.map((region) => {
                  const level = levelForScore(region.compositeScore);
                  const selected = region.stateKey === selectedKey;
                  const severeCount = region.weather?.activeAlerts.filter(
                    (al) => al.severity !== 'MODERATE',
                  ).length;
                  return (
                    <tr
                      key={region.stateKey}
                      onClick={() => onSelectRegion(region.stateKey, region.stateName)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onSelectRegion(region.stateKey, region.stateName);
                        }
                      }}
                      tabIndex={0}
                      aria-label={`${region.stateName}, ${Math.round(region.compositeScore)} composite risk, select region`}
                      className={`group cursor-pointer border-b border-white/5 transition-colors focus-visible:bg-white/5 focus-visible:outline-2 focus-visible:outline-amber-400 ${
                        selected ? 'bg-amber-400/15' : 'hover:bg-white/5'
                      }`}
                    >
                      <th scope="row" className="px-4 py-3 font-medium text-gray-100">
                        {region.stateName}
                      </th>
                      <td className="px-4 py-3 text-right">
                        <span className="tabular-nums text-gray-200">
                          {Math.round(region.compositeScore)}
                        </span>
                        <span className="ml-2 rounded bg-white/10 px-1.5 py-0.5 text-[10px] font-semibold text-gray-300">
                          {level}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-gray-300">
                        {region.projectCount}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-gray-300">
                        {region.disaster?.totalEvents ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-gray-300">
                        {severeCount && severeCount > 0 ? (
                          <span className="font-semibold text-red-300">{severeCount}</span>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  );
                })}
          </tbody>
        </table>
      </div>

      {!isLoading && regions.length === 0 && (
        <div className="px-4 py-8 text-center text-sm text-gray-500">
          No risk data returned yet — check your data source and refresh.
        </div>
      )}
    </section>
  );
}

export const DataTableFallback = memo(DataTableFallbackInner);
