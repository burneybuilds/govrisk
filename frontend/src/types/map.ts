import type { Feature, FeatureCollection } from 'geojson';
import type { RiskLevel } from './index';

export type { FeatureCollection as GeoJsonFeatureCollection };

/** Join key used to relate GeoJSON boundaries to risk data. */
export type StateKey = string;

export const RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const;
export type RiskLevelKey = (typeof RISK_LEVELS)[number];

/**
 * Normalized per-region risk record.
 *
 * Every data source (backend risk API, disaster history, weather alerts) is
 * adapted into this shape via `dataAdapters.ts` before any rendering. Data
 * never reaches the layer components in its raw wire format.
 */
export interface RegionRiskData {
  /** Canonical join key (see `constants/regions.ts`). */
  stateKey: StateKey;
  /** Display name, e.g. "Odisha". */
  stateName: string;
  /** True when any data source contributed records for this region. */
  regionAvailable: boolean;
  /** Composite risk score 0-100 from the portfolio analytics. */
  compositeScore: number;
  riskLevel: RiskLevel;
  /** Number of monitored infrastructure projects in the region. */
  projectCount: number;
  /** Mean risk score across the region's monitored projects. */
  avgRisk: number;
  /** Count of HIGH- and CRITICAL-risk projects in the region. */
  highRiskProjects: number;
  criticalRiskProjects: number;
  /** Short, human-readable list of the highest contributing risk factors. */
  contributingFactors: readonly string[];
  /** Optional historical composite trend for sparklines. Absent when no
   *  history source is wired yet. */
  history?: readonly number[];
  disaster?: DisasterSummary;
  weather?: WeatherSummary;
}

export interface DisasterSummary {
  regionAvailable: boolean;
  totalEvents: number;
  /** Most recent calendar year with recorded events, or null. */
  lastEventYear: number | null;
  /** Frequency of the dominant disaster type in the last 5 years. */
  dominantType: string | null;
  dominantFrequency: number;
  events: readonly DisasterEvent[];
}

export interface DisasterEvent {
  id: string;
  type: 'flood' | 'cyclone' | 'earthquake' | 'drought' | 'landslide' | 'heatwave';
  year: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  magnitude: number | null;
  deaths: number | null;
  displaced: number | null;
}

export interface WeatherSummary {
  regionAvailable: boolean;
  condition: 'CLEAR' | 'MILD' | 'MODERATE' | 'SEVERE' | 'EXTREME' | 'UNKNOWN';
  activeAlerts: readonly WeatherAlert[];
  temperatureC: number | null;
  humidity: number | null;
  windKmh: number | null;
  /** ISO timestamp of the last observation. */
  observedAt: string | null;
}

export interface WeatherAlert {
  id: string;
  type: 'HEAT_WAVE' | 'RAIN' | 'STORM' | 'CYCLONE' | 'FOG' | 'COLD_WAVE' | 'DUST';
  severity: 'MODERATE' | 'SEVERE' | 'EXTREME';
  headline: string;
  issuedAt: string;
  /** Bounding centroid, lat/lng, used to position the pulsing marker. */
  lat: number;
  lng: number;
}

export const PROJECT_STATUSES = ['ONGOING', 'COMPLETED', 'DELAYED', 'STALLED', 'CANCELLED'] as const;
export type ProjectStatus = (typeof PROJECT_STATUSES)[number];

export type ProjectScale = 'MEDIUM' | 'LARGE';

/** A single project point for the graduated risk markers layer. */
export interface ProjectRiskPoint {
  id: string;
  name: string;
  stateName: string;
  riskScore: number;
  riskLevel: RiskLevel;
  costOverrunProbability: number;
  delayProbability: number;
  lat: number;
  lng: number;
  /** Government-ingest provenance (absent for manual projects). */
  status?: ProjectStatus;
  sector?: string;
  agency?: string;
  scale?: ProjectScale;
  fundingSource?: string;
  confidence?: string;
  /** Approved/projected cost in INR crore, source of truth for radius. */
  costEstimateCr?: number;
}

/** Region-level portfolio aggregate from `/api/analytics` riskByState. */
export interface RegionRiskAggregate {
  stateName: string;
  projectCount: number;
  avgRisk: number;
  critical: number;
  high: number;
  compositeScore: number;
  riskLevel: RiskLevel;
}

export interface IndiaRiskMapData {
  points: readonly ProjectRiskPoint[];
  regions: readonly RegionRiskAggregate[];
  /** Portfolio-level factor averages, used by the detail panel breakdown. */
  factorDrivers: readonly FactorDriver[];
}

export interface FactorDriver {
  key: string;
  name: string;
  avgScore: number;
}

/** Which layer drives the region choropleth. Only one at a time. */
export type ChoroplethId = 'risk' | 'disaster';

export type MapLayerId = 'risk' | 'disaster' | 'weather';

export interface MapLayerState {
  /** Region choropleth currently rendered, if any. Exclusive — at most one. */
  choropleth: ChoroplethId | null;
  /** Graduated project markers (independent of the choropleth). */
  riskMarkers: boolean;
  /** Government-ingest infrastructure project layer (status/scale circles). */
  projects: boolean;
  /** Live weather overlay; stacks freely with the choropleth. */
  weatherOverlay: boolean;
  /** Applies to the risk choropleth only. */
  riskOpacity: number;
  /** Applies to the disaster choropleth. */
  disasterOpacity: number;
  /** Weather overlay opacity. */
  weatherOpacity: number;
}

export interface SelectedRegion {
  stateKey: StateKey;
  stateName: string;
}

/** Raw-ish GeoJSON feature used by the boundary layers after validation. */
export interface BoundaryFeature extends Feature {
  properties: RegionFeatureProperties;
}

export interface RegionFeatureProperties {
  state_id?: string;
  name?: string;
  state_name?: string;
  district_id?: string;
}

export interface MapViewport {
  zoom: number;
}
