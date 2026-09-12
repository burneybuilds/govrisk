import { memo, useCallback } from 'react';
import { GeoJSON } from 'react-leaflet';
import type { Feature, FeatureCollection, Geometry, GeoJsonProperties } from 'geojson';
import type { Path } from 'leaflet';
import type { PathOptions } from 'leaflet';
import type { StateKey } from '../../types/map';

/** react-leaflet's GeoJSON style fn receives features as possibly undefined. */
type LeafletFeature = Feature<Geometry, GeoJsonProperties> | undefined;

export interface GeoRegionLayerProps {
  data: FeatureCollection;
  /**
   * Resolve a feature's properties to the canonical state key used to join
   * against region data. Returns null for features without a resolvable key.
   */
  getFeatureKey: (feature: Feature) => StateKey | null;
  getFeatureStyle: (feature: Feature) => PathOptions;
  tooltipContent?: (feature: Feature) => string | null;
  onFeatureSelect?: (key: StateKey, feature: Feature) => void;
  interactive?: boolean;
}

const EMPTY_FEATURE = {} as Feature;

function GeoRegionLayerInner({
  data,
  getFeatureKey,
  getFeatureStyle,
  tooltipContent,
  onFeatureSelect,
  interactive = true,
}: GeoRegionLayerProps) {
  const style = useCallback(
    (feature: LeafletFeature): PathOptions =>
      getFeatureStyle((feature ?? EMPTY_FEATURE) as Feature),
    [getFeatureStyle],
  );

  const onEachFeature = useCallback(
    (feature: Feature, layer: Path) => {
      if (!interactive) return;
      const content = tooltipContent?.(feature) ?? null;
      if (content) {
        layer.bindTooltip(content, {
          className: 'gm-map-tooltip',
          sticky: true,
          direction: 'top',
        });
      }
      const key = getFeatureKey(feature);
      if (key && onFeatureSelect) {
        layer.on('click', () => onFeatureSelect(key, feature));
      }
    },
    [interactive, tooltipContent, getFeatureKey, onFeatureSelect],
  );

  return <GeoJSON data={data} style={style} onEachFeature={onEachFeature} />;
}

/**
 * Memoized so map pans/zooms or legend state changes never rebuild boundary
 * paths unnecessarily.
 */
export const GeoRegionLayer = memo(GeoRegionLayerInner);
