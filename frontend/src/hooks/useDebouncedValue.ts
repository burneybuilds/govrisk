import { useEffect, useState } from 'react';

/**
 * Tracks a fast-changing value through a trailing debounce so expensive work
 * (recomputation, heavy GeoJSON loading decisions) is not triggered on every
 * leaflet move/zoom event.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
