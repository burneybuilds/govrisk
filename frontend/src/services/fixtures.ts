import type { RawDisasterResponse, RawWeatherResponse } from './dataAdapters';

/**
 * DEMO FIXTURES
 * =============
 * Wire-format payloads for the weather and disaster data sources. These match
 * the documented contracts in `validation.ts` and are passed through the SAME
 * zod validation + adapters as a real API response.
 *
 * To wire a real source: set `VITE_WEATHER_API_URL` / `VITE_DISASTER_API_URL`
 * (see `services/mapData.ts`); the env override takes precedence over the
 * fixture below. Keep this file's keys in sync with any endpoint you ship.
 */
const nowIso = new Date().toISOString();

export const DISASTER_FIXTURE: RawDisasterResponse = {
  generatedAt: nowIso,
  regions: [
    {
      stateName: 'Assam',
      history: [
        { type: 'flood', year: 2024, events: 6, severity: 'HIGH', deaths: 40, displaced: 950000 },
        {
          type: 'flood',
          year: 2023,
          events: 5,
          severity: 'CRITICAL',
          deaths: 27,
          displaced: 400000,
        },
        { type: 'flood', year: 2022, events: 4, severity: 'HIGH', deaths: 33, displaced: 700000 },
        { type: 'flood', year: 2021, events: 3, severity: 'HIGH', deaths: 16, displaced: 310000 },
        { type: 'landslide', year: 2024, events: 2, severity: 'HIGH', deaths: 12, displaced: 0 },
      ],
    },
    {
      stateName: 'Bihar',
      history: [
        { type: 'flood', year: 2024, events: 4, severity: 'HIGH', deaths: 14, displaced: 260000 },
        { type: 'heatwave', year: 2023, events: 5, severity: 'CRITICAL', deaths: 44, displaced: 0 },
        { type: 'flood', year: 2022, events: 3, severity: 'MEDIUM', deaths: 9, displaced: 120000 },
      ],
    },
    {
      stateName: 'Odisha',
      history: [
        { type: 'cyclone', year: 2024, events: 2, severity: 'HIGH', deaths: 6, displaced: 58000 },
        {
          type: 'cyclone',
          year: 2023,
          events: 1,
          severity: 'CRITICAL',
          deaths: 11,
          displaced: 120000,
        },
        { type: 'flood', year: 2022, events: 3, severity: 'HIGH', deaths: 7, displaced: 95000 },
        { type: 'drought', year: 2021, events: 2, severity: 'MEDIUM', deaths: 0, displaced: 0 },
      ],
    },
    {
      stateName: 'West Bengal',
      history: [
        { type: 'cyclone', year: 2024, events: 2, severity: 'HIGH', deaths: 9, displaced: 21000 },
        { type: 'flood', year: 2023, events: 4, severity: 'HIGH', deaths: 18, displaced: 180000 },
        {
          type: 'cyclone',
          year: 2021,
          events: 1,
          severity: 'CRITICAL',
          deaths: 4,
          displaced: 15000,
        },
      ],
    },
    {
      stateName: 'Maharashtra',
      history: [
        { type: 'flood', year: 2024, events: 3, severity: 'MEDIUM', deaths: 8, displaced: 42000 },
        { type: 'heatwave', year: 2023, events: 4, severity: 'HIGH', deaths: 21, displaced: 0 },
        { type: 'drought', year: 2022, events: 2, severity: 'MEDIUM', deaths: 0, displaced: 0 },
      ],
    },
    {
      stateName: 'Gujarat',
      history: [
        { type: 'cyclone', year: 2024, events: 1, severity: 'HIGH', deaths: 3, displaced: 9000 },
        { type: 'drought', year: 2023, events: 3, severity: 'HIGH', deaths: 0, displaced: 0 },
        { type: 'heatwave', year: 2022, events: 4, severity: 'CRITICAL', deaths: 31, displaced: 0 },
      ],
    },
    {
      stateName: 'Uttarakhand',
      history: [
        {
          type: 'landslide',
          year: 2023,
          events: 5,
          severity: 'HIGH',
          deaths: 19,
          displaced: 14000,
        },
        {
          type: 'flood',
          year: 2021,
          events: 2,
          severity: 'CRITICAL',
          deaths: 55,
          displaced: 98000,
        },
      ],
    },
    {
      stateName: 'Himachal Pradesh',
      history: [
        { type: 'landslide', year: 2024, events: 3, severity: 'HIGH', deaths: 24, displaced: 5000 },
        { type: 'flood', year: 2023, events: 4, severity: 'HIGH', deaths: 13, displaced: 21000 },
        { type: 'earthquake', year: 2022, events: 1, severity: 'MEDIUM', deaths: 0, displaced: 0 },
      ],
    },
    {
      stateName: 'Rajasthan',
      history: [
        { type: 'heatwave', year: 2024, events: 6, severity: 'CRITICAL', deaths: 63, displaced: 0 },
        { type: 'drought', year: 2023, events: 3, severity: 'HIGH', deaths: 0, displaced: 0 },
        { type: 'heatwave', year: 2022, events: 5, severity: 'HIGH', deaths: 40, displaced: 0 },
      ],
    },
    {
      stateName: 'Karnataka',
      history: [
        { type: 'flood', year: 2022, events: 4, severity: 'HIGH', deaths: 12, displaced: 260000 },
        { type: 'drought', year: 2023, events: 3, severity: 'MEDIUM', deaths: 0, displaced: 0 },
      ],
    },
  ],
};

export const WEATHER_FIXTURE: RawWeatherResponse = {
  observedAt: nowIso,
  regions: [
    {
      stateName: 'Maharashtra',
      condition: 'SEVERE',
      temperatureC: 41.2,
      humidity: 34,
      windKmh: 26,
      alerts: [
        {
          id: 'WX-IN-MH-001',
          type: 'HEAT_WAVE',
          severity: 'SEVERE',
          headline: 'Heat wave over Vidarbha: temperature exceeding 40°C',
          issuedAt: nowIso,
          lat: 20.6,
          lng: 79.1,
        },
        {
          id: 'WX-IN-MH-002',
          type: 'DUST',
          severity: 'MODERATE',
          headline: 'Dust storm expected over Marathwada',
          issuedAt: nowIso,
          lat: 19.1,
          lng: 76.5,
        },
      ],
    },
    {
      stateName: 'Rajasthan',
      condition: 'EXTREME',
      temperatureC: 46.8,
      humidity: 18,
      windKmh: 31,
      alerts: [
        {
          id: 'WX-IN-RJ-001',
          type: 'HEAT_WAVE',
          severity: 'EXTREME',
          headline: 'Extreme heat over west Rajasthan: 46°C+',
          issuedAt: nowIso,
          lat: 26.9,
          lng: 72.5,
        },
      ],
    },
    {
      stateName: 'West Bengal',
      condition: 'MODERATE',
      temperatureC: 33.4,
      humidity: 82,
      windKmh: 44,
      alerts: [
        {
          id: 'WX-IN-WB-001',
          type: 'STORM',
          severity: 'SEVERE',
          headline: 'Severe thunderstorm with squall over south Bengal',
          issuedAt: nowIso,
          lat: 22.5,
          lng: 88.3,
        },
        {
          id: 'WX-IN-WB-002',
          type: 'RAIN',
          severity: 'MODERATE',
          headline: 'Heavy rainfall expected in north districts',
          issuedAt: nowIso,
          lat: 23.9,
          lng: 87.9,
        },
      ],
    },
    {
      stateName: 'Odisha',
      condition: 'SEVERE',
      temperatureC: 36.1,
      humidity: 76,
      windKmh: 58,
      alerts: [
        {
          id: 'WX-IN-OD-001',
          type: 'CYCLONE',
          severity: 'SEVERE',
          headline: 'Cyclonic storm watch along the Odisha coast',
          issuedAt: nowIso,
          lat: 19.8,
          lng: 85.8,
        },
      ],
    },
    {
      stateName: 'Assam',
      condition: 'MODERATE',
      temperatureC: 31.5,
      humidity: 88,
      windKmh: 21,
      alerts: [
        {
          id: 'WX-IN-AS-001',
          type: 'RAIN',
          severity: 'SEVERE',
          headline: 'Very heavy rainfall over Brahmaputra valley',
          issuedAt: nowIso,
          lat: 26.6,
          lng: 92.3,
        },
      ],
    },
    {
      stateName: 'Karnataka',
      condition: 'MILD',
      temperatureC: 28.7,
      humidity: 60,
      windKmh: 14,
      alerts: [],
    },
  ],
};
