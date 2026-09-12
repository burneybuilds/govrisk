import { useCallback, useMemo, useState } from 'react';
import type { ChoroplethId, MapLayerId, MapLayerState } from '../types/map';

const INITIAL_STATE: MapLayerState = {
  choropleth: 'risk',
  riskMarkers: true,
  projects: true,
  weatherOverlay: true,
  riskOpacity: 0.85,
  disasterOpacity: 0.85,
  weatherOpacity: 0.6,
};

export interface MapLayerControls {
  state: MapLayerState;
  /** Set the exclusive region choropleth. */
  setChoropleth: (layer: ChoroplethId) => void;
  clearChoropleth: () => void;
  toggleRiskMarkers: () => void;
  toggleProjects: () => void;
  toggleWeatherOverlay: () => void;
  setOpacity: (layer: MapLayerId, opacity: number) => void;
}

/**
 * Central map layer state. "Only one choropleth at a time" and weather-as-
 * stacking-overlay are enforced here so layer components never coordinate with
 * each other directly (keeps them independently swappable).
 */
export function useMapLayerState(): MapLayerControls {
  const [state, setState] = useState<MapLayerState>(INITIAL_STATE);

  const setChoropleth = useCallback((layer: ChoroplethId) => {
    setState((prev) => ({ ...prev, choropleth: layer }));
  }, []);

  const clearChoropleth = useCallback(() => {
    setState((prev) => ({ ...prev, choropleth: null }));
  }, []);

  const toggleRiskMarkers = useCallback(() => {
    setState((prev) => ({ ...prev, riskMarkers: !prev.riskMarkers }));
  }, []);

  const toggleProjects = useCallback(() => {
    setState((prev) => ({ ...prev, projects: !prev.projects }));
  }, []);

  const toggleWeatherOverlay = useCallback(() => {
    setState((prev) => ({ ...prev, weatherOverlay: !prev.weatherOverlay }));
  }, []);

  const setOpacity = useCallback((layer: MapLayerId, opacity: number) => {
    setState((prev) => ({ ...prev, [`${layer}Opacity` as const]: opacity }));
  }, []);

  return useMemo(
    () => ({
      state,
      setChoropleth,
      clearChoropleth,
      toggleRiskMarkers,
      toggleProjects,
      toggleWeatherOverlay,
      setOpacity,
    }),
    [state, setChoropleth, clearChoropleth, toggleRiskMarkers, toggleProjects, toggleWeatherOverlay, setOpacity],
  );
}
