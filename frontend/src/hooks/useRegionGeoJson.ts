import { useQuery } from '@tanstack/react-query';
import type { FeatureCollection } from 'geojson';
import { DISTRICT_ZOOM_THRESHOLD, QUERY } from '../constants/map';
import { loadDistrictBoundaries, loadStateBoundaries } from '../services/mapData';

/**
 * State boundaries: always required to render the base map.
 */
export function useStateBoundaries() {
  return useQuery({
    queryKey: ['geo', 'states'],
    queryFn: loadStateBoundaries,
    staleTime: QUERY.geo.staleTime,
    retry: QUERY.geo.retry,
    refetchOnWindowFocus: false,
  });
}

export type StateBoundariesResult = ReturnType<typeof useStateBoundaries>;

/**
 * District boundaries: deliberately heavy, so they only load when the user
 * zooms past `DISTRICT_ZOOM_THRESHOLD`. The query stays disabled until then —
 * the country-level view never pays for the district payload.
 */
export function useDistrictBoundaries(zoom: number) {
  const enabled = zoom >= DISTRICT_ZOOM_THRESHOLD;
  return useQuery({
    queryKey: ['geo', 'districts'],
    queryFn: loadDistrictBoundaries,
    enabled,
    staleTime: QUERY.geo.staleTime,
    retry: QUERY.geo.retry,
    refetchOnWindowFocus: false,
  });
}

export type FeatureCollectionResult = ReturnType<typeof useStateBoundaries>;
export type { FeatureCollection };
