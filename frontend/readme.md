# GovRisk Frontend

React + TypeScript + Vite frontend for the GovRisk India infrastructure risk
platform.

## Risk Map

The `/risk-map` page is an interactive, bilingual risk map built on
[react-leaflet](https://react-leaflet.dev). It layers portfolio risk scores,
disaster history markers, and live weather alerts over state-level and
district-level choropleths.

### Data sources

| Layer           | Source                                                            | How to replace                              |
| --------------- | ----------------------------------------------------------------- | ------------------------------------------- |
| Risk choropleth | `GET /api/risk-map` + `GET /api/analytics` (TanStack Query + Zod) | Swap in `services/mapData.ts`               |
| Disaster events | Mock fixtures (`VITE_DISASTER_API_URL`, default off)              | Point env var at an IMD/NDMA-compatible API |
| Weather alerts  | Mock fixtures (`VITE_WEATHER_API_URL`, default off)               | Point env var at a Met/MoES-compatible API  |
| GeoJSON borders | `public/data/india-states.geojson` / `india-districts.geojson`    | Regenerate with `scripts/slim-geojson.mjs`  |

Regions are joined to GeoJSON features by normalized state key
(`resolveStateKey` in `src/utils/geo.ts`), which handles GADM name quirks such
as `Orissa → Odisha` and `Dadra & Nagar Haveli → Daman & Diu`.

### Infrastructure projects ingestion

The backend (`backend/ingest/`) ingests medium/large Indian infrastructure
projects from government portals (data.gov.in, government report extracts)
into the shared project table. Each record carries provenance (`source_name`,
`source_url`, `retrieved_date`, `data_confidence`, `external_ref`) and is
recorded in an append-only `ingest_audit_log`. The map surface is read-only:
it renders whatever `/api/risk-map` returns, so ingestion never blocks the
frontend.

From the `backend` directory:

```bash
python -m ingest.run --source csv_file --file data/sample_projects.csv --dry-run   # review
python -m ingest.run --source csv_file --file data/sample_projects.csv             # apply
python -m ingest.run --source data_gov_in                                          # requires env keys
```

`data/sample_projects.csv` is a **SAMPLE** stand-in for extracted government
reports — replace the columns with real portal extracts, never fabricate
values (missing costs stay NULL and are flagged by confidence). Validate any
new source with `--dry-run` first (`dry_run` mode recomputes the summary
without writing). Backend tests: `python -m unittest discover -s tests`.

### Layers and toggles

- **Risk choropleth** (exclusive): composite portfolio score per state.
- **Disaster choropleth** (exclusive with risk): log-scaled historical event
  intensity; severe districts render pulsing markers.
- **Weather overlay** (independent): stacks on top of either choropleth;
  `MODERATE`/`SEVERE`/`EXTREME` conditions render pulsing markers.
- **Risk markers**: per-project points from the portfolio API.
- **Infrastructure projects (govt)**: government-ingest project layer
  (`ProjectLayer.tsx`). Status colors the marker, scale (or cost) sets the
  radius, clicking opens `ProjectDetailPanel`. Data comes from the same
  `/api/risk-map` payload the risk markers use — the backend derives the
  project-layer fields (`status`, `sector`, `agency`, `scale`, `fundingSource`,
  `confidence`, `costEstimateCr`) from the ingestion provenance.

The layer control panel (`LayerControlPanel.tsx`) exposes opacity sliders,
status dots, and the layer toggles. Color ramps live in `src/constants/map.ts`
(colorblind-safe ColorBrewer schemes); project status colors live in
`src/utils/colors.ts` (`PROJECT_STATUS_COLORS`).

### Interactions

- Click a region to open the **region detail panel** (top factor drivers,
  disaster/weather summaries, join-status diagnostics, and the region's
  exposed infrastructure projects list).
- Click an infrastructure project marker (or a project in the region panel) to
  open the **project detail card** — status, scale, sector, funding source,
  cost estimate, and data confidence.
- Search box + virtualized region list (`@tanstack/react-virtual`) with
  keyboard navigation; `flyTo` on selection.
- `?view=map` / `?view=table` query parameter switches between map and a
  sortable regional data table.
- Districts are loaded lazily past zoom 7 to keep the initial bundle small.

### Adding a layer

1. Extend `RegionRiskData`/`MapLayerState` in `src/types/map.ts`.
2. Fetch + Zod-validate the data in `src/services/mapData.ts`.
3. Compose the react-leaflet layer in `src/components/map/MapContainer.tsx`.
4. Wire the toggle in `useMapLayerState` and `LayerControlPanel`.

### Tooling

- `npm run typecheck` – `tsc -b`
- `npm run lint:eslint` – ESLint 10 + typescript-eslint flat config
- `npm run lint` – oxlint (repo-wide, faster)
- `npm run format` – Prettier
- `npm run test` – Vitest (jsdom)
