import type { BasemapId, ChoroplethId, MapLayerId, RiskLevelKey } from '../types/map';

/** Map visual configuration. */
export const MAP_CENTER: [number, number] = [20.5937, 78.9629];
export const MAP_DEFAULT_ZOOM = 4.5;
export const MAP_MIN_ZOOM = 4;
/** Street-level zoom. Both tile providers carry imagery to z19 (CARTO to z20),
 *  so this is the binding limit for operators inspecting a single site. */
export const MAP_MAX_ZOOM = 19;
export const MAP_MAX_BOUNDS: [[number, number], [number, number]] = [
  [6.5, 68.0],
  [36.5, 98.5],
];

/** Base tiles: muted CartoDB Positron so data layers stay legible.
 *  Override with `VITE_TILE_URL` for a private/authenticated basemap. */
export const BASE_TILE_URL =
  import.meta.env.VITE_TILE_URL ||
  'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
/** Optional key for private/authenticated basemaps (CARTO `key`, Mapbox token, ...). */
export const BASE_TILE_API_KEY =
  (import.meta.env.VITE_TILE_API_KEY as string | undefined) ?? undefined;
/** Tile URL with the auth key appended (no-op when no key set). CARTO cartocdn
 *  tiles carry an "API key required" watermark unless `?key=` is present. */
export const BASE_TILE_URL_WITH_KEY = BASE_TILE_API_KEY
  ? `${BASE_TILE_URL}${BASE_TILE_URL.includes('?') ? '&' : '?'}key=${encodeURIComponent(BASE_TILE_API_KEY)}`
  : BASE_TILE_URL;
export const BASE_TILE_OPTIONS = {
  subdomains: 'abcd',
  maxZoom: 19,
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
} as const;

/** Esri World Imagery. Note the `{z}/{y}/{x}` axis order (not `{z}/{x}/{y}`)
 *  and no `{s}` subdomain — Leaflet does not reorder the placeholders.
 *  Override with `VITE_SATELLITE_TILE_URL` for a private basemap. */
const DEFAULT_SATELLITE_TILE_URL =
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

export const SATELLITE_TILE_URL =
  import.meta.env.VITE_SATELLITE_TILE_URL || DEFAULT_SATELLITE_TILE_URL;

export interface BasemapDefinition {
  id: BasemapId;
  url: string;
  attribution: string;
  /** Tile host rotation; omitted for single-host providers. */
  subdomains?: string;
  /** Photographic/dark imagery — needs stronger boundary contrast. */
  dark?: boolean;
}

/** Selectable basemaps, in switcher order. Exactly one is rendered at a time. */
export const BASEMAPS: Record<BasemapId, BasemapDefinition> = {
  street: {
    id: 'street',
    url: BASE_TILE_URL_WITH_KEY,
    attribution: BASE_TILE_OPTIONS.attribution,
    subdomains: BASE_TILE_OPTIONS.subdomains,
  },
  satellite: {
    id: 'satellite',
    url: SATELLITE_TILE_URL,
    attribution:
      'Imagery &copy; <a href="https://www.esri.com/">Esri</a>, Maxar, Earthstar Geographics, and the GIS User Community',
    dark: true,
  },
};

export const BASEMAP_ORDER: readonly BasemapId[] = ['street', 'satellite'];

/** District boundaries only load once zoomed past this level. */
export const DISTRICT_ZOOM_THRESHOLD = 7;

/** Zoom at which a project click flies in, and where overlay washes begin to
 *  fade so street-level imagery and markers stay readable. */
export const PROJECT_FOCUS_ZOOM = 13;
export const OVERLAY_FADE_START_ZOOM = 8;
export const OVERLAY_FADE_END_ZOOM = 11;

/**
 * Region-scale choropleths are country/region shaped: at street zoom the same
 * polygon covers the entire viewport, washing out the basemap. Fade the wash
 * out between the two thresholds so a deep zoom reveals imagery + markers.
 * Markers are drawn above the overlays and stay fully opaque.
 */
export function overlayOpacityFor(zoom: number, base: number): number {
  if (zoom <= OVERLAY_FADE_START_ZOOM) return base;
  if (zoom >= OVERLAY_FADE_END_ZOOM) return 0;
  const progress = (zoom - OVERLAY_FADE_START_ZOOM) / (OVERLAY_FADE_END_ZOOM - OVERLAY_FADE_START_ZOOM);
  return base * (1 - progress);
}

/** Debounce for pan/zoom events before state settles (ms). */
export const VIEWPORT_DEBOUNCE_MS = 150;
/** Artificial delay for mock fetchers so skeleton loaders are visible (ms). */
export const MOCK_FETCH_DELAY_MS = 500;

/** GeoJSON paths under `public/` (loaded via fetch, not imported). */
export const GEOJSON_PATHS = {
  states: '/data/india-states.geojson',
  districts: '/data/india-districts.geojson',
} as const;

/** react-query freshness windows, chosen per data type. */
export const QUERY = {
  risk: { staleTime: 5 * 60 * 1000, retry: 2 },
  disaster: { staleTime: 60 * 60 * 1000, retry: 2 },
  weather: { staleTime: 10 * 60 * 1000, retry: 3 },
  geo: { staleTime: 24 * 60 * 60 * 1000, retry: 2 },
} as const;

/** Exponential backoff for external (weather) calls. */
export function retryDelay(attempt: number): number {
  return Math.min(1000 * 2 ** attempt, 8000);
}

/**
 * Sequential color ramps (ColorBrewer), colorblind-safe and scientifically
 * standard. Order: low -> high. Index = steps - 1.
 */
export const COLOR_RAMPS = {
  /** Disaster risk choropleth. */
  disaster: [
    '#ffffcc',
    '#ffeda0',
    '#fed976',
    '#feb24c',
    '#fd8d3c',
    '#fc4e2a',
    '#e31a1c',
    '#b10026',
  ],
  /** Weather intensity overlay. */
  weather: ['#eff3ff', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'],
  /** Composite risk score choropleth. */
  risk: ['#fcfbfd', '#efedf5', '#dadaeb', '#bcbddc', '#9e9ac8', '#756bb1', '#54278f', '#3f007d'],
} as const;

export type RampId = keyof typeof COLOR_RAMPS;

/** Weather overlay tile shading (applied as a steady blue tint). */
export const WEATHER_OVERLAY_HEX = '#2171b5';
export const WEATHER_OVERLAY_OPACITY = 0.35;

/** Neutral fill for regions with no data at all. */
export const NO_DATA_FILL = '#e5e7eb';
export const NO_DATA_LABEL = 'No data';

export const REGION_BOUNDARY = { color: '#ffffff', weight: 1, opacity: 0.9 };
export const DISTRICT_BOUNDARY = { color: '#94a3b8', weight: 0.5, opacity: 0.6 };

export interface LayerDefinition {
  id: MapLayerId;
  label: string;
  description: string;
  /** Whether this layer may drive the (exclusive) region choropleth. */
  supportsChoropleth: boolean;
}

export const MAP_LAYERS: readonly LayerDefinition[] = [
  {
    id: 'risk',
    label: 'Composite Risk Score',
    description: 'Portfolio risk aggregated by region',
    supportsChoropleth: true,
  },
  {
    id: 'disaster',
    label: 'Disaster History',
    description: 'Recorded natural hazard exposure by region',
    supportsChoropleth: true,
  },
  {
    id: 'weather',
    label: 'Live Weather Alerts',
    description: 'Active severe weather alerts (independent overlay)',
    supportsChoropleth: false,
  },
];

export const CHOROPLETH_RAMP: Record<ChoroplethId, RampId> = {
  risk: 'risk',
  disaster: 'disaster',
};

/** Risk-level palette for markers/badges; deutan/protan-safe (Okabe-Ito). */
export const RISK_LEVEL_COLORS: Record<RiskLevelKey, string> = {
  LOW: '#0072b2',
  MEDIUM: '#e69f00',
  HIGH: '#d55e00',
  CRITICAL: '#cc3311',
};

export const APP_ACCENT = '#fbbf24'; // amber-400
