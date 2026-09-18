import { memo, useCallback, useMemo } from 'react';
import type { Feature, FeatureCollection } from 'geojson';
import type { ChoroplethRegionLayerProps } from './ChoroplethRegionLayer';
import { ChoroplethRegionLayer } from './ChoroplethRegionLayer';
import { disasterIntensity } from '../../services/dataAdapters';
import type { RegionRiskData, StateKey } from '../../types/map';
import { escapeHtml } from '../../utils/html';
import { resolveFeatureStateKey } from '../../utils/geo';

export interface DisasterLayerProps {
  data: FeatureCollection;
  regions: readonly RegionRiskData[];
  opacity: number;
  selectedKey?: StateKey | null;
  onSelectRegion?: (key: StateKey) => void;
}

function DisasterLayerInner({
  data,
  regions,
  opacity,
  selectedKey = null,
  onSelectRegion,
}: DisasterLayerProps) {
  const values = useMemo(() => {
    const map = new Map<StateKey, number>();
    for (const region of regions) {
      const intensity = disasterIntensity(region.disaster);
      if (intensity !== null) map.set(region.stateKey, intensity);
    }
    return map;
  }, [regions]);

  const getFeatureKey = useCallback((feature: Feature) => resolveFeatureStateKey(feature), []);

  const buildTooltip = useCallback<ChoroplethRegionLayerProps['buildTooltip']>(
    (feature, value) => {
      const name = String(feature.properties?.name ?? feature.properties?.state_name ?? 'Region');
      if (value === null) {
        return `<div class="gm-tooltip-title">${escapeHtml(name)}</div><div class="gm-tooltip-row"><span>No recorded disaster data</span></div>`;
      }
      const region = regions.find((r) => r.stateKey === resolveFeatureStateKey(feature));
      const total = region?.disaster?.totalEvents ?? 0;
      const dominant = region?.disaster?.dominantType ?? '—';
      const lastYear = region?.disaster?.lastEventYear ?? '—';
      return (
        `<div class="gm-tooltip-title">${escapeHtml(name)}</div>` +
        `<div class="gm-tooltip-row"><span>Recorded events</span><b>${total}</b></div>` +
        `<div class="gm-tooltip-row"><span>Dominant hazard</span><b>${escapeHtml(dominant)}</b></div>` +
        `<div class="gm-tooltip-row"><span>Last event</span><b>${lastYear}</b></div>`
      );
    },
    [regions],
  );

  const onSelect = useCallback((key: StateKey) => onSelectRegion?.(key), [onSelectRegion]);

  const handleSelect = useCallback((key: StateKey) => onSelect(key), [onSelect]);

  return (
    <ChoroplethRegionLayer
      data={data}
      values={values}
      ramp="disaster"
      rampSteps={5}
      opacity={opacity}
      getFeatureKey={getFeatureKey}
      buildTooltip={buildTooltip}
      onFeatureSelect={handleSelect}
      selectedKey={selectedKey}
    />
  );
}

export const DisasterLayer = memo(DisasterLayerInner);
