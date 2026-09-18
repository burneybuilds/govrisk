import { useEffect, useState } from 'react';
import { useMap, useMapEvents } from 'react-leaflet';
import { VIEWPORT_DEBOUNCE_MS } from '../../constants/map';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import type { MapViewport } from '../../types/map';

export interface MapViewportTrackerProps {
  onViewport: (viewport: MapViewport) => void;
}

/**
 * Reports the current map zoom (debounced) up the tree so operators can make
 * expensive decisions (e.g. lazy-loading district boundaries) exactly once per
 * settled view change, not on every tile pan frame.
 */
export function MapViewportTracker({ onViewport }: MapViewportTrackerProps) {
  const map = useMap();
  const [zoom, setZoom] = useState<number>(map.getZoom());
  const debouncedZoom = useDebouncedValue(zoom, VIEWPORT_DEBOUNCE_MS);

  useEffect(() => {
    onViewport({ zoom: debouncedZoom });
  }, [debouncedZoom, onViewport]);

  useMapEvents({
    zoomend: () => setZoom(map.getZoom()),
  });

  return null;
}
