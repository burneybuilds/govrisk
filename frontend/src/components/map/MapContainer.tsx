import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer as LeafletMap, TileLayer, ZoomControl, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { Feature } from 'geojson';
import {
  BASE_TILE_URL_WITH_KEY,
  BASE_TILE_OPTIONS,
  DISTRICT_BOUNDARY,
  DISTRICT_ZOOM_THRESHOLD,
  MAP_CENTER,
  MAP_DEFAULT_ZOOM,
  MAP_MAX_BOUNDS,
  MAP_MAX_ZOOM,
  MAP_MIN_ZOOM,
  REGION_BOUNDARY,
} from '../../constants/map';
import { useStateBoundaries, useDistrictBoundaries } from '../../hooks/useRegionGeoJson';
import type {
  FactorDriver,
  MapLayerState,
  ProjectRiskPoint,
  RegionRiskData,
  SelectedRegion,
  StateKey,
} from '../../types/map';
import { resolveFeatureStateKey } from '../../utils/geo';
import { useMapLayerState } from '../../hooks/useMapLayerState';
import { GeoRegionLayer } from './GeoRegionLayer';
import { DisasterLayer } from './DisasterLayer';
import { RiskChoroplethLayer } from './RiskChoroplethLayer';
import { RiskMarkers } from './RiskMarkers';
import { ProjectLayer } from './ProjectLayer';
import { ProjectDetailPanel } from './ProjectDetailPanel';
import { WeatherLayer } from './WeatherLayer';
import { MapViewportTracker } from './MapViewportTracker';
import { RegionSearch } from './RegionSearch';
import { LayerControlPanel, type LayerDataStatus } from './LayerControlPanel';
import { MapLegend } from './MapLegend';
import { RegionDetailPanel } from './RegionDetailPanel';
import { MapStatusBanner } from './MapStatusBanner';
import { Skeleton } from './Skeleton';
import { escapeHtml } from '../../utils/html';
import './leaflet-overrides.css';

export interface MapContainerProps {
  regions: readonly RegionRiskData[];
  points: readonly ProjectRiskPoint[];
  factorDrivers: readonly FactorDriver[];
  dataStatus: LayerDataStatus;
  isInitialLoading: boolean;
  layerState: MapLayerState;
  layerControls: ReturnType<typeof useMapLayerState>;
  onSelectRegion?: (key: StateKey, stateName: string) => void;
}

function statusFor(status: {
  isLoading: boolean;
  isError: boolean;
}): 'error' | 'loading' | 'ready' {
  if (status.isError) return 'error';
  if (status.isLoading) return 'loading';
  return 'ready';
}

/** Flies the map to a region whenever the selection changes (user-panned safe). */
function SelectedRegionFollower({
  selectedKey,
  featuresByKey,
}: {
  selectedKey: StateKey | null;
  featuresByKey: ReadonlyMap<StateKey, Feature>;
}) {
  const map = useMap();
  const first = useRef(true);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (!selectedKey) return;
    const feature = featuresByKey.get(selectedKey);
    if (!feature) return;
    const bounds = L.geoJSON(feature).getBounds();
    if (bounds.isValid()) {
      map.flyToBounds(bounds, { padding: [80, 80], maxZoom: 7, duration: 0.6 });
    }
  }, [selectedKey, featuresByKey, map]);

  return null;
}

/** Zoom to the selected project's location so its area is in view. */
function SelectedProjectFollower({
  selectedProject,
}: {
  selectedProject: ProjectRiskPoint | null;
}) {
  const map = useMap();
  const first = useRef(true);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (!selectedProject) return;
    const { lat, lng } = selectedProject;
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
    map.flyTo([lat, lng], PROJECT_FOCUS_ZOOM, { duration: 0.6 });
  }, [selectedProject, map]);

  return null;
}

const PROJECT_FOCUS_ZOOM = 9;

export function MapContainer({
  regions,
  points,
  factorDrivers,
  dataStatus,
  isInitialLoading,
  layerState,
  layerControls,
  onSelectRegion,
}: MapContainerProps) {
  const [viewportZoom, setViewportZoom] = useState<number>(MAP_DEFAULT_ZOOM);
  const [selected, setSelected] = useState<SelectedRegion | null>(null);
  const [selectedProject, setSelectedProject] = useState<ProjectRiskPoint | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);

  const statesQuery = useStateBoundaries();
  const districtsQuery = useDistrictBoundaries(viewportZoom);

  const featuresByKey = useMemo(() => {
    const map = new Map<StateKey, Feature>();
    for (const feature of statesQuery.data?.features ?? []) {
      const key = resolveFeatureStateKey(feature);
      if (key) map.set(key, feature);
    }
    return map;
  }, [statesQuery.data]);

  const alerts = useMemo(() => regions.flatMap((r) => r.weather?.activeAlerts ?? []), [regions]);

  const selectedKey = selected?.stateKey ?? null;

  const handleSelectRegion = useCallback(
    (key: StateKey | null, stateName?: string) => {
      if (!key) {
        setSelected(null);
        return;
      }
      const region = regions.find((r) => r.stateKey === key);
      const name = region?.stateName ?? stateName ?? key;
      setSelected({ stateKey: key, stateName: name });
      setPanelOpen(true);
      onSelectRegion?.(key, name);
    },
    [regions, onSelectRegion],
  );

  const handleLayerSelect = useCallback(
    (key: StateKey) => handleSelectRegion(key),
    [handleSelectRegion],
  );

  const handleFeatureSelect = useCallback(
    (key: StateKey, feature: Feature) => {
      const name = String(feature.properties?.name ?? feature.properties?.state_name ?? key);
      handleSelectRegion(key, name);
    },
    [handleSelectRegion],
  );

  const handleSelectProject = useCallback((point: ProjectRiskPoint) => {
    setSelectedProject(point);
  }, []);

  const handleCloseProject = useCallback(() => {
    setSelectedProject(null);
  }, []);

  const handleDistrictSelect = useCallback(
    (key: StateKey, feature: Feature) => {
      const stateFeature = featuresByKey.get(key) ?? feature;
      handleFeatureSelect(key, stateFeature);
    },
    [featuresByKey, handleFeatureSelect],
  );

  const baseStatesStyle = useCallback(
    (): L.PathOptions => ({
      fillColor: 'transparent',
      color: REGION_BOUNDARY.color,
      weight: REGION_BOUNDARY.weight,
      opacity: REGION_BOUNDARY.opacity,
    }),
    [],
  );

  const districtStyle = useCallback(
    (): L.PathOptions => ({
      fill: false,
      color: DISTRICT_BOUNDARY.color,
      weight: DISTRICT_BOUNDARY.weight,
      opacity: DISTRICT_BOUNDARY.opacity,
    }),
    [],
  );

  const districtTooltip = useCallback((feature: Feature) => {
    const name = String(feature.properties?.name ?? 'District');
    const state = String(feature.properties?.state_name ?? '');
    return `<div class="gm-tooltip-title">${escapeHtml(name)}</div>${
      state ? `<div class="gm-tooltip-row"><span>${escapeHtml(state)}</span></div>` : ''
    }`;
  }, []);

  const riskChoroplethOn = layerState.choropleth === 'risk' && !dataStatus.risk.isError;
  const disasterChoroplethOn = layerState.choropleth === 'disaster' && !dataStatus.disaster.isError;
  const weatherOn = layerState.weatherOverlay && !dataStatus.weather.isError;

  const chipText = (() => {
    if (isInitialLoading) return 'Syncing live risk sources…';
    const broken: string[] = [];
    if (dataStatus.risk.isError) broken.push('risk');
    if (dataStatus.disaster.isError) broken.push('disaster');
    if (dataStatus.weather.isError) broken.push('weather');
    if (broken.length > 0) return `Partial data: ${broken.join(', ')} currently unreachable`;
    return null;
  })();

  const statesAreUnavailable = statesQuery.isError;
  const showDistricts = viewportZoom >= DISTRICT_ZOOM_THRESHOLD && !!districtsQuery.data;

  return (
    <div className="relative h-full w-full overflow-hidden">
      <LeafletMap
        center={MAP_CENTER}
        zoom={MAP_DEFAULT_ZOOM}
        minZoom={MAP_MIN_ZOOM}
        maxZoom={MAP_MAX_ZOOM}
        maxBounds={MAP_MAX_BOUNDS as L.LatLngBoundsExpression}
        maxBoundsViscosity={0.8}
        zoomControl={false}
        className="h-full w-full bg-navy-950"
        preferCanvas
      >
        <TileLayer
          url={BASE_TILE_URL_WITH_KEY}
          attribution={BASE_TILE_OPTIONS.attribution}
          maxZoom={MAP_MAX_ZOOM}
        />
        <ZoomControl position="bottomright" />
        <MapViewportTracker onViewport={({ zoom }) => setViewportZoom(zoom)} />

        {showDistricts && (
          <GeoRegionLayer
            data={districtsQuery.data}
            getFeatureKey={resolveFeatureStateKey}
            getFeatureStyle={districtStyle}
            tooltipContent={districtTooltip}
            onFeatureSelect={handleDistrictSelect}
          />
        )}

        {statesQuery.data && (
          <GeoRegionLayer
            data={statesQuery.data}
            getFeatureKey={resolveFeatureStateKey}
            getFeatureStyle={baseStatesStyle}
            onFeatureSelect={handleFeatureSelect}
          />
        )}

        {weatherOn && statesQuery.data && (
          <WeatherLayer
            data={statesQuery.data}
            regions={regions}
            alerts={alerts}
            opacity={layerState.weatherOpacity}
            selectedKey={selectedKey}
            onSelectRegion={handleLayerSelect}
          />
        )}

        {disasterChoroplethOn && statesQuery.data && (
          <DisasterLayer
            data={statesQuery.data}
            regions={regions}
            opacity={layerState.disasterOpacity}
            selectedKey={selectedKey}
            onSelectRegion={handleLayerSelect}
          />
        )}

        {riskChoroplethOn && statesQuery.data && (
          <RiskChoroplethLayer
            data={statesQuery.data}
            regions={regions}
            opacity={layerState.riskOpacity}
            selectedKey={selectedKey}
            onSelectRegion={handleLayerSelect}
          />
        )}

        {layerState.riskMarkers && !dataStatus.risk.isError && points.length > 0 && (
          <RiskMarkers
            points={points}
            selectedKey={selectedKey}
            onSelectRegion={handleLayerSelect}
          />
        )}

        {layerState.projects && !dataStatus.projects.isError && points.length > 0 && (
          <ProjectLayer
            points={points}
            selectedProjectId={selectedProject?.id}
            onSelectProject={handleSelectProject}
          />
        )}

        <SelectedRegionFollower selectedKey={selectedKey} featuresByKey={featuresByKey} />
        <SelectedProjectFollower selectedProject={selectedProject} />
        <RegionSearch
          regions={regions}
          featuresByKey={featuresByKey}
          onSelect={handleSelectRegion}
        />
        <LayerControlPanel
          layerState={layerState}
          dataStatus={dataStatus}
          onSetChoropleth={layerControls.setChoropleth}
          onClearChoropleth={layerControls.clearChoropleth}
          onToggleRiskMarkers={layerControls.toggleRiskMarkers}
          onToggleProjects={layerControls.toggleProjects}
          onToggleWeatherOverlay={layerControls.toggleWeatherOverlay}
          onSetOpacity={layerControls.setOpacity}
        />
        <MapLegend
          layerState={layerState}
          activeChoropleth={riskChoroplethOn ? 'risk' : disasterChoroplethOn ? 'disaster' : null}
          hasMarkers={points.length > 0}
        />
      </LeafletMap>

      {/* Skeleton / status overlays sit above the leaflet container as a single
          stacked column so transient messages never collide with each other,
          the search box, or the layer panel. */}
      <div className="absolute left-3 top-14 z-[500] flex max-w-[300px] flex-col items-start gap-2">
        {statesQuery.isLoading && (
          <div className="flex items-center gap-2 rounded-md border border-white/10 bg-[#141e35]/90 px-3 py-2 text-xs text-gray-200 shadow-lg backdrop-blur">
            <Skeleton className="h-3 w-3 rounded-full" />
            <span>Loading boundary geometry…</span>
          </div>
        )}
        {statesAreUnavailable && (
          <div
            role="alert"
            className="max-w-[260px] rounded-md border border-red-500/40 bg-[#2a1420]/90 px-3 py-2 text-xs text-red-100"
          >
            Boundary geometry unavailable — showing data layers only.
          </div>
        )}
        {riskChoroplethOn && <MapStatusBanner layer="risk" status={statusFor(dataStatus.risk)} />}
        {disasterChoroplethOn && (
          <MapStatusBanner layer="disaster" status={statusFor(dataStatus.disaster)} />
        )}
        {weatherOn && <MapStatusBanner layer="weather" status={statusFor(dataStatus.weather)} />}
        {chipText && (
          <div className="rounded-md border border-white/10 bg-[#0f1830]/90 px-3 py-2 text-xs text-gray-300 shadow-lg backdrop-blur">
            {chipText}
          </div>
        )}
      </div>

      {/* Region intelligence panel (desktop right / mobile bottom sheet). */}
      {panelOpen && (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-[600] px-3 pb-3 md:top-14 md:left-auto md:right-3 md:w-[360px] md:max-h-[calc(100vh_-_4.25rem_-_30px)] md:px-0 md:pb-0">
          <RegionDetailPanel
            selected={selected}
            regions={regions}
            factorDrivers={factorDrivers}
            points={points}
            status={dataStatus}
            onClose={() => {
              setSelected(null);
              setPanelOpen(false);
            }}
            onSelectRegion={handleSelectRegion}
            onSelectProject={handleSelectProject}
          />
        </div>
      )}

      {/* Project details (opened from the project layer or region panel). */}
      {selectedProject && (
        <div className="pointer-events-none absolute top-16 left-3 right-3 z-[600] md:left-1/2 md:right-auto md:w-[300px] md:-translate-x-1/2">
          <ProjectDetailPanel project={selectedProject} onClose={handleCloseProject} />
        </div>
      )}
      {!panelOpen && (
        <button
          type="button"
          onClick={() => setPanelOpen(true)}
          className="absolute bottom-3 left-1/2 z-[600] -translate-x-1/2 rounded-full border border-white/10 bg-[#0f1830]/95 px-4 py-2 text-sm font-semibold text-amber-300 shadow-xl backdrop-blur hover:text-amber-200 focus-visible:outline-2 focus-visible:outline-amber-400"
        >
          Browse regions
        </button>
      )}
    </div>
  );
}
