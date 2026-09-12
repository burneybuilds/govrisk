/**
 * Slims the raw India GADM GeoJSON files for the risk map.
 *
 * - Rounds coordinates to 4 decimal places (~11 m precision, ample for
 *   administrative boundary display) which cuts payload size dramatically.
 * - Drops GADM boilerplate properties, keeping only the join keys the map
 *   actually uses:
 *     states   -> NAME_1 (state name), ID_1 (gadm state id)
 *     districts-> NAME_1, ID_1, NAME_2 (district name), ID_2
 *
 * Input files (downloaded from https://github.com/geohacker/india):
 *   - frontend/public/data/india-states.geojson
 *   - frontend/public/data/india-districts.geojson
 *
 * Usage: node scripts/slim-geojson.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'public', 'data');

const STATS = {
  'india-states.geojson': {
    props: (p) => ({ state_id: String(p.ID_1), name: p.NAME_1 }),
  },
  'india-districts.geojson': {
    props: (p) => ({
      state_id: String(p.ID_1),
      state_name: p.NAME_1,
      district_id: String(p.ID_2),
      name: p.NAME_2,
    }),
  },
};

function roundPos(pos) {
  return [Math.round(pos[0] * 10000) / 10000, Math.round(pos[1] * 10000) / 10000];
}

function roundGeom(geom) {
  if (geom.type === 'Point') {
    return { ...geom, coordinates: roundPos(geom.coordinates) };
  }
  if (geom.type === 'MultiPoint') {
    return { ...geom, coordinates: geom.coordinates.map(roundPos) };
  }
  if (geom.type === 'LineString') {
    return { ...geom, coordinates: geom.coordinates.map(roundPos) };
  }
  if (geom.type === 'MultiLineString') {
    return { ...geom, coordinates: geom.coordinates.map((part) => part.map(roundPos)) };
  }
  if (geom.type === 'Polygon') {
    return { ...geom, coordinates: geom.coordinates.map((ring) => ring.map(roundPos)) };
  }
  if (geom.type === 'MultiPolygon') {
    return {
      ...geom,
      coordinates: geom.coordinates.map((poly) => poly.map((ring) => ring.map(roundPos))),
    };
  }
  if (geom.type === 'GeometryCollection') {
    return { ...geom, geometries: geom.geometries.map(roundGeom) };
  }
  return geom;
}

for (const [file, { props }] of Object.entries(STATS)) {
  const inputPath = path.join(root, file);
  if (!fs.existsSync(inputPath)) {
    console.warn(`skipping ${file}: not found`);
    continue;
  }
  const raw = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const features = raw.features.map((f) => ({
    type: 'Feature',
    properties: props(f.properties ?? {}),
    geometry: roundGeom(f.geometry),
  }));

  const out = JSON.stringify({ type: 'FeatureCollection', features });
  fs.writeFileSync(inputPath, out, 'utf8');
  const before = Math.round(fs.statSync(inputPath).size);
  console.log(
    `${file}: ${raw.features.length} features, ${(before / 1e6).toFixed(2)} MB -> ${(out.length / 1e6).toFixed(2)} MB`,
  );
}
