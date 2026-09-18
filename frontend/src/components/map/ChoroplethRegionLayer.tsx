import { memo, useCallback } from 'react';
import type { Feature, FeatureCollection } from 'geojson';
import type { PathOptions } from 'leaflet';
import { NO_DATA_FILL, REGION_BOUNDARY } from '../../constants/map';
import type { RampId } from '../../constants/map';
import type { StateKey } from '../../types/map';
import { quantileColor } from '../../utils/colors';
import { GeoRegionLayer } from './GeoRegionLayer';

export interface ChoroplethRegionLayerProps {
  data: FeatureCollection;
  /** feature stateKey -> normalized 0..1 intensity (missing = no data). */
  values: ReadonlyMap<StateKey, number>;
  ramp: RampId;
  rampSteps?: number;
  opacity: number;
  getFeatureKey: (feature: Feature) => StateKey | null;
  buildTooltip: (feature: Feature, value: number | null) => string;
  onFeatureSelect?: (key: StateKey, feature: Feature) => void;
  selectedKey?: StateKey | null;
}

function getValue(
  feature: Feature,
  getFeatureKey: ChoroplethRegionLayerProps['getFeatureKey'],
  values: ReadonlyMap<StateKey, number>,
): { key: StateKey | null; value: number | null } {
  const key = getFeatureKey(feature);
  if (!key) return { key: null, value: null };
  const value = values.get(key);
  return { key, value: value === undefined ? null : value };
}

function ChoroplethRegionLayerInner({
  data,
  values,
  ramp,
  rampSteps = 5,
  opacity,
  getFeatureKey,
  buildTooltip,
  onFeatureSelect,
  selectedKey = null,
}: ChoroplethRegionLayerProps) {
  const getFeatureStyle = useCallback(
    (feature: Feature): PathOptions => {
      const { key, value } = getValue(feature, getFeatureKey, values);
      const selected = selectedKey !== null && key === selectedKey;
      return {
        fillColor: quantileColor(value, ramp, rampSteps),
        fillOpacity: opacity,
        color: selected ? '#fbbf24' : REGION_BOUNDARY.color,
        weight: selected ? 2.5 : REGION_BOUNDARY.weight,
        opacity: selected ? 1 : REGION_BOUNDARY.opacity,
      };
    },
    [values, ramp, rampSteps, opacity, getFeatureKey, selectedKey],
  );

  const tooltipContent = useCallback(
    (feature: Feature): string => {
      const { value } = getValue(feature, getFeatureKey, values);
      return buildTooltip(feature, value);
    },
    [getFeatureKey, values, buildTooltip],
  );

  const handleSelect = useCallback(
    (key: StateKey, feature: Feature) => onFeatureSelect?.(key, feature),
    [onFeatureSelect],
  );

  return (
    <GeoRegionLayer
      data={data}
      getFeatureKey={getFeatureKey}
      getFeatureStyle={getFeatureStyle}
      tooltipContent={tooltipContent}
      onFeatureSelect={handleSelect}
    />
  );
}

/**
 * Region choropleth driven by a normalized intensity map. Single source of
 * truth for "how to paint regions"; disaster/risk/weather all feed into it.
 */
export const ChoroplethRegionLayer = memo(ChoroplethRegionLayerInner);
export { NO_DATA_FILL };
