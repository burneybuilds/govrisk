import type { MapLayerId } from '../../types/map';
import { Skeleton } from './Skeleton';

export type LayerStatus = 'loading' | 'error' | 'ready' | 'idle';

export interface MapStatusBannerProps {
  layer: MapLayerId;
  status: LayerStatus;
  /** Optional per-layer re-fetch action. */
  onRetry?: () => void;
}

const LAYER_TITLES: Record<MapLayerId, string> = {
  risk: 'Risk intelligence',
  disaster: 'Disaster history',
  weather: 'Weather overlay',
};

/**
 * Small inline status strip that lives with its layer: skeleton while loading,
 * a labelled error with retry when the (possibly external) source fails, and
 * nothing when ready. Every layer fails independently.
 */
export function MapStatusBanner({ layer, status, onRetry }: MapStatusBannerProps) {
  if (status !== 'loading' && status !== 'error') return null;

  const title = LAYER_TITLES[layer];

  if (status === 'loading') {
    return (
      <div className="pointer-events-none relative flex items-center gap-2 rounded-md border border-white/10 bg-[#141e35]/90 px-3 py-2 text-xs text-gray-200 shadow-lg backdrop-blur">
        <Skeleton className="h-3 w-3 rounded-full" />
        <span>Loading {title.toLowerCase()}…</span>
      </div>
    );
  }

  return (
    <div
      role="alert"
      className="relative flex max-w-[260px] items-center gap-2 rounded-md border border-red-500/40 bg-[#2a1420]/90 px-3 py-2 text-xs text-red-100 shadow-lg backdrop-blur"
    >
      <span className="flex-none">{title} unavailable — showing partial data.</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="ml-1 flex-none rounded border border-red-400/50 px-1.5 py-0.5 font-semibold text-red-200 hover:bg-red-500/20 focus-visible:outline-2 focus-visible:outline-amber-400"
        >
          Retry
        </button>
      )}
    </div>
  );
}
