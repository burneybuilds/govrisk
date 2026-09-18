import { memo, useState } from 'react';
import type { ChoroplethId, MapLayerId, MapLayerState } from '../../types/map';
import type { RampId } from '../../constants/map';
import { rampLegend } from '../../utils/colors';
import { useI18n } from '../../i18n';
import { Skeleton } from './Skeleton';

export type LayerDataStatus = {
  risk: { isLoading: boolean; isError: boolean };
  disaster: { isLoading: boolean; isError: boolean };
  weather: { isLoading: boolean; isError: boolean };
  projects: { isLoading: boolean; isError: boolean };
};

export interface LayerControlPanelProps {
  layerState: MapLayerState;
  dataStatus: LayerDataStatus;
  onSetChoropleth: (layer: ChoroplethId) => void;
  onClearChoropleth: () => void;
  onToggleRiskMarkers: () => void;
  onToggleProjects: () => void;
  onToggleWeatherOverlay: () => void;
  onSetOpacity: (layer: MapLayerId, opacity: number) => void;
}

function ColorRampPreview({ ramp }: { ramp: RampId }) {
  const stops = rampLegend(ramp, 5).map((s) => s.color);
  return (
    <span
      className="mr-[25px] h-1 w-10 shrink-0 rounded-full"
      style={{
        background: `linear-gradient(90deg, ${stops.join(', ')})`,
      }}
      aria-hidden="true"
    />
  );
}

function StatusDot({
  status,
  t,
}: {
  status: { isLoading: boolean; isError: boolean };
  t: ReturnType<typeof useI18n>['t'];
}) {
  if (status.isLoading) {
    return (
      <span className="h-2 w-2 animate-pulse rounded-full bg-amber-300/80" aria-hidden="true" />
    );
  }
  if (status.isError) {
    return (
      <span
        className="h-2 w-2 rounded-full bg-red-400/90"
        title={t('map.sourceUnavailable')}
        aria-label={t('map.sourceUnavailable')}
      />
    );
  }
  return (
    <span
      className="h-2 w-2 rounded-full bg-emerald-400/90"
      title={t('map.ready')}
      aria-label={t('map.ready')}
    />
  );
}

function LayerControlPanelInner({
  layerState,
  dataStatus,
  onSetChoropleth,
  onClearChoropleth,
  onToggleRiskMarkers,
  onToggleProjects,
  onToggleWeatherOverlay,
  onSetOpacity,
}: LayerControlPanelProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(true);

  const riskChecked = layerState.choropleth === 'risk';
  const disasterChecked = layerState.choropleth === 'disaster';

  return (
    <div
      className="absolute right-3 top-3 z-[700] w-64 overflow-hidden rounded-md border border-white/10 bg-[#0f1830]/90 text-gray-200 shadow-2xl backdrop-blur"
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="layer-control-panel"
        className="flex w-full items-center justify-between px-3 py-2 text-sm font-semibold text-amber-300 hover:text-amber-200 focus-visible:outline-2 focus-visible:outline-amber-400"
      >
        <span>{t('map.layers')}</span>
        <span aria-hidden="true">{open ? '−' : '+'}</span>
      </button>

      {open && (
        <div id="layer-control-panel" className="space-y-3 px-3 pb-3">
          <fieldset>
            <legend className="mb-1 text-[11px] font-medium uppercase tracking-wider text-gray-400">
              {t('map.choroplethLegend')}
            </legend>
            <label className="flex cursor-pointer items-center justify-between gap-2 rounded px-2 py-1.5 hover:bg-white/5">
              <span className="flex min-w-0 items-center gap-2 text-[13px]">
                <input
                  type="checkbox"
                  checked={riskChecked}
                  onChange={(e) =>
                    e.target.checked ? onSetChoropleth('risk') : onClearChoropleth()
                  }
                  className="h-4 w-4 shrink-0 accent-purple-500"
                />
                {t('map.riskScoreLayer')}
                <StatusDot status={dataStatus.risk} t={t} />
              </span>
              <ColorRampPreview ramp="risk" />
            </label>
            {riskChecked && (
              <label className="flex items-center gap-2 pl-6 text-[11px] text-gray-400">
                <span className="w-16">Opacity</span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={layerState.riskOpacity}
                  onChange={(e) => onSetOpacity('risk', Number(e.target.value))}
                  className="h-1.5 min-w-0 flex-1 accent-purple-400"
                  aria-label="Risk choropleth opacity"
                />
                <span className="w-8 text-right tabular-nums">
                  {Math.round(layerState.riskOpacity * 100)}%
                </span>
              </label>
            )}

            <label className="flex cursor-pointer items-center justify-between gap-2 rounded px-2 py-1.5 hover:bg-white/5">
              <span className="flex min-w-0 items-center gap-2 text-[13px]">
                <input
                  type="checkbox"
                  checked={disasterChecked}
                  onChange={(e) =>
                    e.target.checked ? onSetChoropleth('disaster') : onClearChoropleth()
                  }
                  className="h-4 w-4 shrink-0 accent-orange-500"
                />
                Disaster history
                <StatusDot status={dataStatus.disaster} />
              </span>
              <ColorRampPreview ramp="disaster" />
            </label>
            {disasterChecked && (
              <label className="flex items-center gap-2 pl-6 text-[11px] text-gray-400">
                <span className="w-16">Opacity</span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={layerState.disasterOpacity}
                  onChange={(e) => onSetOpacity('disaster', Number(e.target.value))}
                  className="h-1.5 min-w-0 flex-1 accent-orange-400"
                  aria-label="Disaster choropleth opacity"
                />
                <span className="w-8 text-right tabular-nums">
                  {Math.round(layerState.disasterOpacity * 100)}%
                </span>
              </label>
            )}
          </fieldset>

          <div className="border-t border-white/10" />

          <div className="space-y-1.5">
            <label className="flex cursor-pointer items-center justify-between gap-2 rounded px-2 py-1.5 text-[13px] hover:bg-white/5">
              <span className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={layerState.riskMarkers}
                  onChange={onToggleRiskMarkers}
                  className="h-4 w-4 accent-purple-500"
                />
                Project markers
              </span>
              <StatusDot status={dataStatus.projects} />
            </label>

            <label className="flex cursor-pointer items-center justify-between gap-2 rounded px-2 py-1.5 text-[13px] hover:bg-white/5">
              <span className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={layerState.projects}
                  onChange={onToggleProjects}
                  className="h-4 w-4 accent-cyan-500"
                />
                Infrastructure projects
                <StatusDot status={dataStatus.projects} />
              </span>
              <span className="text-[10px] uppercase tracking-wide text-cyan-400/80">
                Govt
              </span>
            </label>

            <label className="flex cursor-pointer items-center justify-between gap-2 rounded px-2 py-1.5 text-[13px] hover:bg-white/5">
              <span className="flex min-w-0 items-center gap-2">
                <input
                  type="checkbox"
                  checked={layerState.weatherOverlay}
                  onChange={onToggleWeatherOverlay}
                  className="h-4 w-4 shrink-0 accent-blue-500"
                />
                Weather overlay
                <StatusDot status={dataStatus.weather} />
              </span>
              <ColorRampPreview ramp="weather" />
            </label>
            {layerState.weatherOverlay && (
              <label className="flex items-center gap-2 pl-6 text-[11px] text-gray-400">
                <span className="w-16">Opacity</span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={layerState.weatherOpacity}
                  onChange={(e) => onSetOpacity('weather', Number(e.target.value))}
                  className="h-1.5 min-w-0 flex-1 accent-blue-400"
                  aria-label="Weather overlay opacity"
                />
                <span className="w-8 text-right tabular-nums">
                  {Math.round(layerState.weatherOpacity * 100)}%
                </span>
              </label>
            )}
          </div>

          {dataStatus.risk.isLoading ||
          dataStatus.disaster.isLoading ||
          dataStatus.weather.isLoading ||
          dataStatus.projects.isLoading ? (
            <div className="flex items-center gap-2 px-2 py-1 text-[11px] text-gray-400">
              <Skeleton className="h-3 w-3" />
              Loading sources…
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

export const LayerControlPanel = memo(LayerControlPanelInner);
