import { Feature, Geometry, Position, FeatureCollection } from 'geojson';
import type { StateKey } from '../types/map';
import { resolveStateKey } from '../constants/regions';

const BAD_GEOJSON = 'INVALID_GEOJSON';

/**
 * Canonical state key for a boundary feature. Prefers the explicit `state_id`
 * property when present, then falls back to a fuzzy name resolution so both the
 * GADM dataset (`name` = "Orissa") and backend state names join cleanly.
 */
export function resolveFeatureStateKey(feature: Feature): StateKey | null {
  const props = feature.properties ?? {};
  const name = props.name ?? props.state_name;
  if (typeof name === 'string') {
    const resolved = resolveStateKey(name);
    if (resolved) return resolved;
  }
  if (typeof props.state_name === 'string') {
    const resolved = resolveStateKey(props.state_name);
    if (resolved) return resolved;
  }
  const stateId = props.state_id;
  if (typeof stateId === 'string' && stateId.length > 0) {
    return stateId as StateKey;
  }
  return null;
}

/**
 * Structurally validate a GeoJSON FeatureCollection fetched from the network.
 * Geometry depth is intentionally shallow — boundary files are large and from
 * trusted sources; we only guard against a corrupt payload, not malicious
 * coordinates.
 */
export function isFeatureCollection(value: unknown): value is FeatureCollection {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as { type?: unknown; features?: unknown };
  if (obj.type !== 'FeatureCollection') return false;
  if (!Array.isArray(obj.features) || obj.features.length === 0) return false;
  return obj.features.every((feature) => {
    if (typeof feature !== 'object' || feature === null) return false;
    const f = feature as { type?: unknown; geometry?: unknown };
    return f.type === 'Feature' && typeof f.geometry === 'object' && f.geometry !== null;
  });
}

/** Parse a boundaries payload and throw a typed error if it is malformed. */
export function parseFeatureCollection(raw: string): FeatureCollection {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new Error(BAD_GEOJSON);
  }
  if (!isFeatureCollection(value)) {
    throw new Error(BAD_GEOJSON);
  }
  return value;
}

function visitPositions(geometry: Geometry, onPosition: (p: Position) => void): void {
  switch (geometry.type) {
    case 'Point':
      onPosition(geometry.coordinates);
      break;
    case 'MultiPoint':
      geometry.coordinates.forEach(onPosition);
      break;
    case 'LineString':
      geometry.coordinates.forEach(onPosition);
      break;
    case 'MultiLineString':
      geometry.coordinates.forEach((line) => line.forEach(onPosition));
      break;
    case 'Polygon':
      geometry.coordinates.forEach((ring) => ring.forEach(onPosition));
      break;
    case 'MultiPolygon':
      geometry.coordinates.forEach((poly) => poly.forEach((ring) => ring.forEach(onPosition)));
      break;
    default:
      break;
  }
}

/**
 * Cheap centroid estimation for a GeoJSON geometry — the arithmetic mean of all
 * vertices. Accurate enough for region labels on a country-scale map, and
 * avoids pulling a full geojson library just for one number.
 */
export function geometryCentroid(geometry: Geometry): [number, number] {
  let latSum = 0;
  let lngSum = 0;
  let count = 0;
  visitPositions(geometry, ([lng, lat]) => {
    lngSum += lng;
    latSum += lat;
    count += 1;
  });
  if (count === 0) return [0, 0];
  return [latSum / count, lngSum / count];
}

export { BAD_GEOJSON };
