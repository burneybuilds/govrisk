import { memo } from 'react';
import { MapIcon, Satellite } from 'lucide-react';
import type { BasemapId } from '../../types/map';
import { BASEMAP_ORDER } from '../../constants/map';
import { useI18n, type TranslationKey } from '../../i18n';

export interface BasemapSwitcherProps {
  basemap: BasemapId;
  onChange: (basemap: BasemapId) => void;
}

const LABELS: Record<BasemapId, TranslationKey> = {
  street: 'map.basemapStreet',
  satellite: 'map.basemapSatellite',
};

/**
 * Standalone street/satellite toggle.
 *
 * Deliberately NOT nested in `LayerControlPanel`: that panel is anchored to the
 * right edge at the same offset as `RegionDetailPanel`, so anything added to it
 * overlaps the region panel. This control is rendered into the left overlay
 * column, which is a flex stack and therefore cannot self-overlap.
 */
function BasemapSwitcherInner({ basemap, onChange }: BasemapSwitcherProps) {
  const { t } = useI18n();

  return (
    <div className="rounded-md border border-white/10 bg-[#0f1830]/90 p-0.5 shadow-lg backdrop-blur">
      <div role="radiogroup" aria-label={t('map.basemap')} className="grid grid-cols-2 gap-0.5">
        {BASEMAP_ORDER.map((id) => {
          const selected = basemap === id;
          const Icon = id === 'satellite' ? Satellite : MapIcon;
          return (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(id)}
              className={`flex items-center justify-center gap-1.5 rounded px-2 py-1.5 text-[12px] font-medium transition-colors ${
                selected
                  ? 'bg-amber-400/20 text-amber-200'
                  : 'text-gray-300 hover:bg-white/5 hover:text-gray-100'
              }`}
            >
              <Icon size={13} aria-hidden="true" />
              {t(LABELS[id])}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export const BasemapSwitcher = memo(BasemapSwitcherInner);
