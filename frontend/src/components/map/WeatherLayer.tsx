import { memo, useCallback, useMemo } from 'react';
import { Marker, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import type { Feature, FeatureCollection } from 'geojson';
import { ChoroplethRegionLayer, type ChoroplethRegionLayerProps } from './ChoroplethRegionLayer';
import { weatherIntensity } from '../../services/dataAdapters';
import type { RegionRiskData, StateKey, WeatherAlert } from '../../types/map';
import { escapeHtml } from '../../utils/html';
import { resolveFeatureStateKey } from '../../utils/geo';

export interface WeatherLayerProps {
  data: FeatureCollection;
  regions: readonly RegionRiskData[];
  /** All active alerts across the country (only severe ones get markers). */
  alerts: readonly WeatherAlert[];
  opacity: number;
  selectedKey?: StateKey | null;
  onSelectRegion?: (key: StateKey) => void;
}

function buildAlertIcon(extreme: boolean): L.DivIcon {
  return L.divIcon({
    className: '',
    html: `<div class="gm-pulse-wrap" role="img" aria-label="Severe weather alert">
      <span class="gm-pulse-ring${extreme ? ' gm-pulse-ring--extreme' : ''}"></span>
      <span class="gm-pulse-dot${extreme ? ' gm-pulse-dot--extreme' : ''}"></span>
    </div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

const SEVERE_ICON = buildAlertIcon(false);
const EXTREME_ICON = buildAlertIcon(true);

function PulsingAlerts({ alerts }: { alerts: readonly WeatherAlert[] }) {
  const visible = useMemo(() => alerts.filter((a) => a.severity !== 'MODERATE'), [alerts]);
  return (
    <>
      {visible.map((alert) => (
        <Marker
          key={alert.id}
          position={[alert.lat, alert.lng]}
          icon={alert.severity === 'EXTREME' ? EXTREME_ICON : SEVERE_ICON}
          zIndexOffset={800}
        >
          <Tooltip className="gm-map-tooltip" direction="top" offset={[0, -10]}>
            <div className="gm-tooltip-title">{escapeHtml(alert.headline)}</div>
          </Tooltip>
        </Marker>
      ))}
    </>
  );
}

const MemoizedPulsingAlerts = memo(PulsingAlerts);

function WeatherLayerInner({
  data,
  regions,
  alerts,
  opacity,
  selectedKey = null,
  onSelectRegion,
}: WeatherLayerProps) {
  const values = useMemo(() => {
    const map = new Map<StateKey, number>();
    for (const region of regions) {
      const intensity = weatherIntensity(region.weather);
      if (intensity !== null) map.set(region.stateKey, intensity);
    }
    return map;
  }, [regions]);

  const getFeatureKey = useCallback((feature: Feature) => resolveFeatureStateKey(feature), []);

  const buildTooltip = useCallback<ChoroplethRegionLayerProps['buildTooltip']>(
    (feature, value) => {
      const name = String(feature.properties?.name ?? feature.properties?.state_name ?? 'Region');
      if (value === null) {
        return `<div class="gm-tooltip-title">${escapeHtml(name)}</div><div class="gm-tooltip-row"><span>No weather snapshot</span></div>`;
      }
      const key = resolveFeatureStateKey(feature);
      const region = key ? regions.find((r) => r.stateKey === key) : undefined;
      const condition = region?.weather?.condition ?? '—';
      const alertsCount = region?.weather?.activeAlerts.length ?? 0;
      return (
        `<div class="gm-tooltip-title">${escapeHtml(name)}</div>` +
        `<div class="gm-tooltip-row"><span>Condition</span><b>${escapeHtml(condition)}</b></div>` +
        `<div class="gm-tooltip-row"><span>Active alerts</span><b>${alertsCount}</b></div>`
      );
    },
    [regions],
  );

  const handleSelect = useCallback((key: StateKey) => onSelectRegion?.(key), [onSelectRegion]);

  return (
    <>
      <ChoroplethRegionLayer
        data={data}
        values={values}
        ramp="weather"
        rampSteps={5}
        opacity={opacity}
        getFeatureKey={getFeatureKey}
        buildTooltip={buildTooltip}
        onFeatureSelect={handleSelect}
        selectedKey={selectedKey}
      />
      <MemoizedPulsingAlerts alerts={alerts} />
    </>
  );
}

/**
 * Live weather layer: a blue intensity overlay plus pulsing markers for active
 * severe alerts. Independent of the exclusive choropleth — stacks freely.
 */
export const WeatherLayer = memo(WeatherLayerInner);
