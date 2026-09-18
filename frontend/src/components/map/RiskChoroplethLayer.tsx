import { memo, useCallback, useMemo } from 'react';
import type { Feature, FeatureCollection } from 'geojson';
import { ChoroplethRegionLayer, type ChoroplethRegionLayerProps } from './ChoroplethRegionLayer';
import { riskIntensity } from '../../services/dataAdapters';
import type { RegionRiskData, StateKey } from '../../types/map';
import { escapeHtml } from '../../utils/html';
import { resolveFeatureStateKey } from '../../utils/geo';

export interface RiskChoroplethLayerProps {
  data: FeatureCollection;
  regions: readonly RegionRiskData[];
  opacity: number;
  selectedKey?: StateKey | null;
  onSelectRegion?: (key: StateKey) => void;
}

function RiskChoroplethLayerInner({
  data,
  regions,
  opacity,
  selectedKey = null,
  onSelectRegion,
}: RiskChoroplethLayerProps) {
  const values = useMemo(() => {
    const map = new Map<StateKey, number>();
    for (const region of regions) {
      map.set(region.stateKey, riskIntensity(region));
    }
    return map;
  }, [regions]);

  const getFeatureKey = useCallback((feature: Feature) => resolveFeatureStateKey(feature), []);

  const buildTooltip = useCallback<ChoroplethRegionLayerProps['buildTooltip']>(
    (feature, value) => {
      const name = String(feature.properties?.name ?? feature.properties?.state_name ?? 'Region');
      if (value === null) {
        return `<div class="gm-tooltip-title">${escapeHtml(name)}</div><div class="gm-tooltip-row"><span>No monitored projects</span></div>`;
      }
      const key = resolveFeatureStateKey(feature);
      const region = key ? regions.find((r) => r.stateKey === key) : undefined;
      const score = region?.compositeScore ?? 0;
      const projects = region?.projectCount ?? 0;
      const level = region?.riskLevel ?? '—';
      return (
        `<div class="gm-tooltip-title">${escapeHtml(name)}</div>` +
        `<div class="gm-tooltip-row"><span>Composite risk</span><b>${Math.round(score)}/100</b></div>` +
        `<div class="gm-tooltip-row"><span>Level</span><b>${escapeHtml(level)}</b></div>` +
        `<div class="gm-tooltip-row"><span>Projects</span><b>${projects}</b></div>`
      );
    },
    [regions],
  );

  const handleSelect = useCallback((key: StateKey) => onSelectRegion?.(key), [onSelectRegion]);

  return (
    <ChoroplethRegionLayer
      data={data}
      values={values}
      ramp="risk"
      rampSteps={5}
      opacity={opacity}
      getFeatureKey={getFeatureKey}
      buildTooltip={buildTooltip}
      onFeatureSelect={handleSelect}
      selectedKey={selectedKey}
    />
  );
}

export const RiskChoroplethLayer = memo(RiskChoroplethLayerInner);
