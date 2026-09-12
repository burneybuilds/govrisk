import { memo, useMemo, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { RegionRiskData, StateKey } from '../../types/map';
import { levelForScore } from '../../constants/regions';
import { Skeleton } from './Skeleton';

export interface RegionListProps {
  regions: readonly RegionRiskData[];
  selectedKey?: StateKey | null;
  onSelect: (key: StateKey, stateName: string) => void;
  isLoading?: boolean;
  maxHeight?: number;
  filter?: string;
}

const ROW_HEIGHT = 48;

function RegionListInner({
  regions,
  selectedKey = null,
  onSelect,
  isLoading = false,
  maxHeight = 420,
  filter = '',
}: RegionListProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const rows = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const source = q ? regions.filter((r) => r.stateName.toLowerCase().includes(q)) : regions;
    return [...source].sort((a, b) => b.compositeScore - a.compositeScore);
  }, [regions, filter]);

  const virtualizer = useVirtualizer({
    count: isLoading ? 0 : rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 6,
  });

  return (
    <div
      ref={parentRef}
      className="overflow-y-auto rounded-md border border-white/10"
      style={{ height: Math.min(maxHeight, Math.max(88, rows.length * ROW_HEIGHT)) }}
      aria-label="Region list"
      role="listbox"
    >
      <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
        {isLoading
          ? Array.from({ length: 8 }, (_, i) => (
              <div key={i} className="flex items-center gap-3 px-3" style={{ height: ROW_HEIGHT }}>
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-3 w-10" />
              </div>
            ))
          : virtualizer.getVirtualItems().map((virtualRow) => {
              const region = rows[virtualRow.index];
              const level = levelForScore(region.compositeScore);
              const selected = region.stateKey === selectedKey;
              return (
                <button
                  key={virtualRow.key}
                  id={`region-row-${region.stateKey}`}
                  role="option"
                  aria-selected={selected}
                  type="button"
                  onClick={() => onSelect(region.stateKey, region.stateName)}
                  className={`absolute left-0 top-0 flex w-full items-center justify-between gap-2 px-3 text-left text-[13px] ${
                    selected ? 'bg-amber-400/20 text-amber-200' : 'text-gray-200 hover:bg-white/5'
                  }`}
                  style={{
                    height: virtualRow.size,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  <span className="truncate">{region.stateName}</span>
                  <span className="flex flex-none items-center gap-2">
                    <span className="tabular-nums text-gray-400">{region.projectCount} proj</span>
                    <span
                      className={`inline-block w-16 rounded px-1.5 py-0.5 text-center text-[10px] font-semibold ${
                        selected ? 'bg-amber-300/20 text-amber-200' : 'bg-white/10 text-gray-300'
                      }`}
                    >
                      {level} · {Math.round(region.compositeScore)}
                    </span>
                  </span>
                </button>
              );
            })}
      </div>
      {!isLoading && rows.length === 0 && (
        <div className="px-3 py-4 text-center text-xs text-gray-500">No regions match.</div>
      )}
    </div>
  );
}

/** Virtualized, score-sorted list of regions used by the detail panel. */
export const RegionList = memo(RegionListInner);
