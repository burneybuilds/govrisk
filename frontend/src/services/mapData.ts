import type { FeatureCollection } from 'geojson';
import { GEOJSON_PATHS, MOCK_FETCH_DELAY_MS } from '../constants/map';
import type {
  IndiaRiskMapData,
  RegionRiskData,
  StateKey,
  DisasterSummary,
  WeatherSummary,
} from '../types/map';
import { parseFeatureCollection } from '../utils/geo';
import {
  adaptDisasterData,
  adaptRiskAggregates,
  adaptRiskMapPoints,
  adaptTopRiskFactors,
  adaptWeatherData,
  buildRegionRiskData,
} from './dataAdapters';
import { DISASTER_FIXTURE, WEATHER_FIXTURE } from './fixtures';
import { getAnalytics, getRiskMapData } from './api';

/** Requests to external providers time out fast; react-query retries with
 *  exponential backoff via `retryDelay`. */
const EXTERNAL_TIMEOUT_MS = 8000;
const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

async function fetchTextWithTimeout(url: string, timeoutMs: number): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) throw new Error(`Request failed: ${res.status} ${res.statusText}`);
    return await res.text();
  } finally {
    clearTimeout(timer);
  }
}

async function fetchExternalJson(url: string): Promise<unknown> {
  const text = await fetchTextWithTimeout(url, EXTERNAL_TIMEOUT_MS);
  return JSON.parse(text);
}

// ---------------------------------------------------------------------------
// Risk scores (backend)
// ---------------------------------------------------------------------------

interface RawAnalyticsResponse {
  riskByState?: unknown;
  topRiskFactors?: unknown;
}

/** Validate + shape both backend risk endpoints into one structure. */
export async function loadRiskScores(): Promise<IndiaRiskMapData> {
  const [pointsRaw, analyticsRaw] = await Promise.all([getRiskMapData(), getAnalytics()]);
  const analytics = analyticsRaw as RawAnalyticsResponse;
  const hasRiskByState = Array.isArray(analytics?.riskByState);
  const hasTopRiskFactors = Array.isArray(analytics?.topRiskFactors);
  return {
    points: adaptRiskMapPoints(pointsRaw),
    regions: hasRiskByState ? adaptRiskAggregates(analytics.riskByState) : [],
    factorDrivers: hasTopRiskFactors ? adaptTopRiskFactors(analytics.topRiskFactors) : [],
  };
}

// ---------------------------------------------------------------------------
// Disaster + weather (pluggable fetchers)
// ---------------------------------------------------------------------------

function envOr(url: string | undefined, fallback: unknown) {
  if (!url) return fallback;
  return fetchExternalJson(url);
}

/** Disaster history source. Prefers `VITE_DISASTER_API_URL`, else fixture. */
export async function loadDisasterData(): Promise<ReadonlyMap<StateKey, DisasterSummary>> {
  const url = import.meta.env.VITE_DISASTER_API_URL as string | undefined;
  const raw = await envOr(url, DISASTER_FIXTURE);
  if (!url) await delay(MOCK_FETCH_DELAY_MS);
  return adaptDisasterData(raw);
}

/** Weather source. Prefers `VITE_WEATHER_API_URL`, else fixture. */
export async function loadWeatherData(): Promise<ReadonlyMap<StateKey, WeatherSummary>> {
  const url = import.meta.env.VITE_WEATHER_API_URL as string | undefined;
  const raw = await envOr(url, WEATHER_FIXTURE);
  if (!url) await delay(MOCK_FETCH_DELAY_MS);
  return adaptWeatherData(raw);
}

// ---------------------------------------------------------------------------
// GeoJSON boundaries
// ---------------------------------------------------------------------------

/** State boundaries — always loaded (needed for the base map colors). */
export async function loadStateBoundaries(): Promise<FeatureCollection> {
  const text = await fetchTextWithTimeout(GEOJSON_PATHS.states, EXTERNAL_TIMEOUT_MS);
  return parseFeatureCollection(text);
}

/** District boundaries — lazy, only fetched on user request (zoomed in). */
export async function loadDistrictBoundaries(): Promise<FeatureCollection> {
  const text = await fetchTextWithTimeout(GEOJSON_PATHS.districts, EXTERNAL_TIMEOUT_MS);
  return parseFeatureCollection(text);
}

// ---------------------------------------------------------------------------
// Combined normalized region data (merges the three sources)
// ---------------------------------------------------------------------------

export async function loadRegionRiskData(): Promise<RegionRiskData[]> {
  const [risk, disasters, weather] = await Promise.all([
    loadRiskScores(),
    loadDisasterData(),
    loadWeatherData(),
  ]);
  return buildRegionRiskData({
    aggregates: [...risk.regions],
    disasters,
    weather,
  });
}
