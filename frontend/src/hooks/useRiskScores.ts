import { useQuery } from '@tanstack/react-query';
import { QUERY } from '../constants/map';
import { loadRiskScores } from '../services/mapData';
import type { IndiaRiskMapData } from '../types/map';

/**
 * Portfolio risk scores from the backend. Stale time is deliberately short so
 * dashboard/project updates propagate to the map quickly.
 */
export function useRiskScores() {
  return useQuery({
    queryKey: ['risk-map', 'scores'],
    queryFn: loadRiskScores,
    staleTime: QUERY.risk.staleTime,
    retry: QUERY.risk.retry,
    refetchOnWindowFocus: false,
  });
}

export type RiskScoresResult = ReturnType<typeof useRiskScores>;
export type { IndiaRiskMapData };
