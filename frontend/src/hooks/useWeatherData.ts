import { useQuery } from '@tanstack/react-query';
import { QUERY, retryDelay } from '../constants/map';
import { loadWeatherData } from '../services/mapData';
import type { StateKey, WeatherSummary } from '../types/map';

/**
 * Weather is live data. We want freshness, so staleTime is short; the retry
 * budget is higher than the other layers because weather feeds are flaky
 * (free-tier quota limits, provider hiccups).
 */
export function useWeatherData() {
  return useQuery({
    queryKey: ['risk-map', 'weather'],
    queryFn: loadWeatherData,
    staleTime: QUERY.weather.staleTime,
    retry: QUERY.weather.retry,
    retryDelay: retryDelay,
    refetchOnWindowFocus: false,
  });
}

export type WeatherDataResult = ReturnType<typeof useWeatherData>;
export type { StateKey, WeatherSummary };
