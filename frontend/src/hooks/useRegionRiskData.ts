import { useMemo } from 'react';
import { useDisasterData } from './useDisasterData';
import { useRiskScores } from './useRiskScores';
import { useWeatherData } from './useWeatherData';
import { buildRegionRiskData } from '../services/dataAdapters';
import type { RegionRiskData } from '../types/map';

export interface RegionRiskDataResult {
  regions: readonly RegionRiskData[];
  /** True only while every contributing source is still loading. */
  isInitialLoading: boolean;
  /** Per-layer fetch outcomes so each fails independently. */
  status: {
    risk: { isLoading: boolean; isError: boolean };
    disaster: { isLoading: boolean; isError: boolean };
    weather: { isLoading: boolean; isError: boolean };
    /** Project-layer data comes from the same /api/risk-map payload. */
    projects: { isLoading: boolean; isError: boolean };
  };
}

/**
 * Compose the three independent data hooks into the normalized region schema.
 * A failure in any single layer surfaces as `status.<layer>.isError` and never
 * blocks the other layers from rendering.
 */
export function useRegionRiskData(): RegionRiskDataResult {
  const risk = useRiskScores();
  const disaster = useDisasterData();
  const weather = useWeatherData();

  const regions = useMemo(
    () =>
      buildRegionRiskData({
        aggregates: [...(risk.data?.regions ?? [])],
        disasters: disaster.data ?? new Map(),
        weather: weather.data ?? new Map(),
      }),
    [risk.data, disaster.data, weather.data],
  );

  return {
    regions,
    isInitialLoading: risk.isLoading && disaster.isLoading && weather.isLoading,
    status: {
      risk: { isLoading: risk.isLoading, isError: risk.isError },
      disaster: { isLoading: disaster.isLoading, isError: disaster.isError },
      weather: { isLoading: weather.isLoading, isError: weather.isError },
      projects: { isLoading: risk.isLoading, isError: risk.isError },
    },
  };
}
