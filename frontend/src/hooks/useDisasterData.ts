import { useQuery } from '@tanstack/react-query';
import { QUERY, retryDelay } from '../constants/map';
import { loadDisasterData } from '../services/mapData';
import type { DisasterSummary, StateKey } from '../types/map';

/**
 * Disaster history is broad and slow-moving — cache aggressively, retry a few
 * times if the source blips.
 */
export function useDisasterData() {
  return useQuery({
    queryKey: ['risk-map', 'disaster'],
    queryFn: loadDisasterData,
    staleTime: QUERY.disaster.staleTime,
    retry: QUERY.disaster.retry,
    retryDelay: retryDelay,
    refetchOnWindowFocus: false,
  });
}

export type DisasterDataResult = ReturnType<typeof useDisasterData>;
export type { DisasterSummary, StateKey };
