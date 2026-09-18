import { memo, useCallback, useMemo, useRef, useState } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import type { Feature } from 'geojson';
import type { RegionRiskData, StateKey } from '../../types/map';
import { levelForScore } from '../../constants/regions';

export interface RegionSearchProps {
  regions: readonly RegionRiskData[];
  /** stateKey -> state boundary feature (for flying to bounds). */
  featuresByKey: ReadonlyMap<StateKey, Feature>;
  onSelect: (key: StateKey, stateName: string) => void;
}

const MAX_RESULTS = 16;

function RegionSearchInner({ regions, featuresByKey, onSelect }: RegionSearchProps) {
  const map = useMap();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return regions.filter((r) => r.stateName.toLowerCase().includes(q)).slice(0, MAX_RESULTS);
  }, [regions, query]);

  const goTo = useCallback(
    (key: StateKey, stateName: string) => {
      const feature = featuresByKey.get(key);
      if (feature) {
        const bounds = L.geoJSON(feature).getBounds();
        if (bounds.isValid()) {
          map.flyToBounds(bounds, { padding: [40, 40], maxZoom: 7 });
        }
      }
      onSelect(key, stateName);
      setOpen(false);
      setQuery('');
      setActiveIndex(-1);
      inputRef.current?.blur();
    },
    [featuresByKey, map, onSelect],
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setOpen(true);
        setActiveIndex((i) => Math.min(i + 1, Math.max(results.length - 1, 0)));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const pick = results[activeIndex >= 0 ? activeIndex : 0];
        if (pick) goTo(pick.stateKey, pick.stateName);
      } else if (e.key === 'Escape') {
        setOpen(false);
        setActiveIndex(-1);
      }
    },
    [results, activeIndex, goTo],
  );

  return (
    <div className="absolute left-3 top-3 z-[500] w-64">
      <div className="relative">
        <input
          ref={inputRef}
          type="search"
          role="combobox"
          aria-expanded={open}
          aria-controls="region-search-listbox"
          aria-autocomplete="list"
          aria-activedescendant={activeIndex >= 0 ? `region-option-${activeIndex}` : undefined}
          placeholder="Search a state…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            setActiveIndex(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          onBlur={() => setOpen(false)}
          className="w-full rounded-md border border-white/10 bg-[#0f1830]/90 px-3 py-2 text-sm text-gray-100 placeholder:text-gray-500 shadow-lg backdrop-blur focus:border-amber-400 focus:outline-none"
        />
      </div>
      {open && results.length > 0 && (
        <ul
          id="region-search-listbox"
          role="listbox"
          className="mt-1 max-h-72 overflow-y-auto rounded-md border border-white/10 bg-[#0f1830]/95 py-1 text-sm shadow-xl backdrop-blur"
        >
          {results.map((region, i) => {
            const level = levelForScore(region.compositeScore);
            const active = i === activeIndex;
            return (
              <li
                key={region.stateKey}
                id={`region-option-${i}`}
                role="option"
                aria-selected={active}
                onMouseDown={(e) => {
                  e.preventDefault();
                  goTo(region.stateKey, region.stateName);
                }}
                onMouseEnter={() => setActiveIndex(i)}
                className={`flex cursor-pointer items-center justify-between gap-2 px-3 py-1.5 text-[13px] ${
                  active ? 'bg-amber-400/20 text-amber-200' : 'text-gray-200 hover:bg-white/5'
                }`}
              >
                <span>{region.stateName}</span>
                <span className={`tabular-nums ${active ? 'text-amber-200' : 'text-gray-400'}`}>
                  {Math.round(region.compositeScore)} · {level}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export const RegionSearch = memo(RegionSearchInner);
