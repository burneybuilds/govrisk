import { memo, useMemo } from 'react';
import type { ChoroplethId, MapLayerState } from '../../types/map';
import type { RampId } from '../../constants/map';
import { COLOR_RAMPS } from '../../constants/map';
import { rampLegend, PROJECT_STATUS_COLORS } from '../../utils/colors';
import type { ProjectStatus } from '../../types/map';

export interface MapLegendProps {
  layerState: MapLayerState;
  /** Highest intensity unit shown on whichever ramp is active. */
  activeChoropleth?: ChoroplethId | null;
  hasMarkers: boolean;
}

const TITLES: Record<ChoroplethId, { title: string; min: string; max: string }> = {
  risk: { title: 'Composite risk score', min: '0', max: '100' },
  disaster: { title: 'Recorded disaster events', min: 'Low', max: 'High' },
};

function MapLegendInner({ layerState, activeChoropleth, hasMarkers }: MapLegendProps) {
  const active: RampId | null =
    activeChoropleth ?? (layerState.weatherOverlay ? ('weather' as const) : null);

  const legend = useMemo(() => {
    if (!active) return null;
    const stops = rampLegend(active, 5).map((s) => s.color);
    if (active === 'weather') {
      return { title: 'Weather conditions', stops, min: 'Calm', max: 'Extreme' };
    }
    const def = TITLES[active];
    return { ...def, stops };
  }, [active]);

  if (!legend) return null;

  return (
    <div className="absolute bottom-6 left-3 z-[500] rounded-md border border-white/10 bg-[#0f1830]/90 px-3 py-2 text-[11px] text-gray-300 shadow-lg backdrop-blur">
      <div className="mb-1 font-semibold text-gray-100">{legend.title}</div>
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-gray-400">{legend.min}</span>
        <span
          className="h-2.5 w-28 rounded-full"
          style={{ background: `linear-gradient(90deg, ${legend.stops.join(', ')})` }}
          aria-hidden="true"
        />
        <span className="text-[10px] text-gray-400">{legend.max}</span>
      </div>
      {hasMarkers && layerState.riskMarkers && (
        <div className="mt-2 flex items-center gap-2 border-t border-white/10 pt-2">
          <span aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 18 18">
              <circle
                cx="9"
                cy="9"
                r="7"
                fill={COLOR_RAMPS.risk[3]}
                stroke="#ffffff"
                strokeWidth="1.2"
              />
            </svg>
          </span>
          <span>A monitored project · size ∝ risk score</span>
        </div>
      )}
      {layerState.projects && (
        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 border-t border-white/10 pt-2">
          {STATUS_ORDER.map((status) => (
            <span key={status} className="flex items-center gap-1.5 text-[10px] capitalize">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: PROJECT_STATUS_COLORS[status] }}
                aria-hidden="true"
              />
              {status.toLowerCase()}
            </span>
          ))}
          <span className="col-span-2 mt-0.5 text-[10px] text-gray-500">
            size = scale (small/large)
          </span>
        </div>
      )}
    </div>
  );
}

const STATUS_ORDER: readonly ProjectStatus[] = [
  'ONGOING',
  'COMPLETED',
  'DELAYED',
  'STALLED',
  'CANCELLED',
];

export const MapLegend = memo(MapLegendInner);
